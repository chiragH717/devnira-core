import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from spec.approved_company_genesis import stage_verified_company_genesis,GenesisApprovalError
from scripts.stage_company_genesis_local import create_bundle_files,ROOT
from spec.ss58_company_account import encode_ss58_account
from spec.genesis_candidate import LIQUID,LOCKED

ADDRESS=encode_ss58_account(bytes(range(1,33)))
ALT=encode_ss58_account(bytes(range(2,34)))
NOW=datetime(2026,10,14,12,0,0,tzinfo=timezone.utc)
LAUNCH=NOW+timedelta(days=90)

class SecureGenesisHandoffTests(unittest.TestCase):
    def setUp(self):
        self.proposal=json.loads((ROOT/"config/genesis-proposal.json").read_text())
        self.certificate={"schema":"public-cert"}
        self.verified={
            "company_address":ADDRESS,
            "public_key_hex":"0x"+"ab"*100,
            "ownership_signature_verified":True,
            "verifier_sha256":"c"*64,
        }

    @patch("spec.approved_company_genesis.verify_company_certificate")
    def test_verified_public_owner_gets_exact_non_live_genesis_plan(self, verify):
        verify.return_value=self.verified
        result=stage_verified_company_genesis(
            self.proposal,self.certificate,Path("/no-company-private-key"),
            "c"*64,LAUNCH,now=NOW)
        verify.assert_called_once()
        self.assertEqual(result["approved_offchain_proposal"]["company_treasury"]["public_address"],ADDRESS)
        self.assertEqual(result["approved_offchain_proposal"]["team_investor_founder_vesting"]["beneficiary_addresses"],[ADDRESS])
        self.assertIsNone(self.proposal["company_treasury"]["public_address"])
        self.assertFalse(result["production_genesis"])
        self.assertFalse(result["network_live"])
        plan=result["checked_genesis_inputs"]
        self.assertFalse(plan["runnable_chain_spec"])
        self.assertEqual(plan["initial_account_balances_units"][0],[ADDRESS,LIQUID])
        self.assertEqual(plan["initial_account_balances_units"][1][1],LOCKED)
        self.assertEqual(len(plan["onchain_vesting_schedules_absolute_ms"]),12)
        self.assertEqual(sum(a[4] for a in plan["onchain_vesting_schedules_absolute_ms"]),LOCKED)

    @patch("spec.approved_company_genesis.verify_company_certificate")
    def test_rejects_conflicting_company_and_any_premine(self, verify):
        verify.return_value=self.verified
        for path,bad in (
            ("company_treasury",{"public_address":ALT}),
            ("initial_balances",[["Alice",100]]),
            ("max_supply_units",100),
            ("mining_allocation_units",100),
            ("genesis_timestamp_ms",1),
        ):
            proposal=copy.deepcopy(self.proposal)
            if path=="company_treasury":
                proposal[path].update(bad)
            else:
                proposal[path]=bad
            with self.assertRaises((GenesisApprovalError,ValueError)):
                stage_verified_company_genesis(proposal,self.certificate,Path("/stub"),
                                               "c"*64,LAUNCH,now=NOW)

    @patch("spec.approved_company_genesis.verify_company_certificate")
    def test_rejects_expired_or_invalid_native_signature_and_past_time(self, verify):
        verify.side_effect=ValueError("bad native signature")
        with self.assertRaisesRegex(ValueError,"bad native"):
            stage_verified_company_genesis(self.proposal,{},Path("/stub"),
                                           "c"*64,LAUNCH,now=NOW)
        verify.side_effect=None
        verify.return_value=dict(self.verified,ownership_signature_verified=False)
        with self.assertRaisesRegex(GenesisApprovalError,"signature"):
            stage_verified_company_genesis(self.proposal,{},Path("/stub"),
                                           "c"*64,LAUNCH,now=NOW)
        verify.return_value=self.verified
        with self.assertRaisesRegex(GenesisApprovalError,"future"):
            stage_verified_company_genesis(self.proposal,{},Path("/stub"),
                                           "c"*64,NOW,now=NOW)

    @patch("spec.approved_company_genesis.verify_company_certificate")
    def test_offline_review_files_are_not_committed_or_overwritten(self, verify):
        verify.return_value=self.verified
        result=stage_verified_company_genesis(self.proposal,{},Path("/stub"),"c"*64,LAUNCH,now=NOW)
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/"review"
            create_bundle_files(result,folder)
            self.assertEqual(len(list(folder.iterdir())),3)
            self.assertTrue(all("private" not in p.name for p in folder.iterdir()))
            with self.assertRaises(FileExistsError):
                create_bundle_files(result,folder)
        with self.assertRaisesRegex(ValueError,"OUTSIDE"):
            create_bundle_files(result,ROOT/"bad-company-genesis-output")

if __name__=="__main__":
    unittest.main()
