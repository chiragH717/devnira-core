import copy
import json
import unittest
from pathlib import Path

from spec.genesis_candidate import GenesisInputError, LIQUID, LOCKED, construct_inputs
from spec.ss58_company_account import encode_ss58_account
from spec.vesting_pot import vesting_pot_ss58

PROJECT = Path(__file__).resolve().parents[1]

class GenesisCandidateTests(unittest.TestCase):
    def setUp(self):
        self.proposal = json.loads((PROJECT / "config/genesis-proposal.json").read_text())
        self.addr = encode_ss58_account(bytes(range(1,33)))
        self.proposal["company_treasury"]["public_address"] = self.addr
        self.proposal["genesis_timestamp_ms"] = 1801411200000

    def test_exact_3m_7m_and_12_cliffs_non_deployable(self):
        values = construct_inputs(self.proposal)
        self.assertFalse(values["runnable_chain_spec"])
        self.assertFalse(values["production_genesis"])
        self.assertEqual(values["initial_account_balances_units"],
                         [[self.addr, LIQUID], [vesting_pot_ss58(), LOCKED]])
        self.assertEqual(sum(x[1] for x in values["initial_account_balances_units"]),
                         10_000_000 * 100_000_000)
        self.assertEqual(len(values["onchain_vesting_schedules_absolute_ms"]), 12)
        self.assertEqual(sum(x[-1] for x in values["onchain_vesting_schedules_absolute_ms"]), LOCKED)
        self.assertEqual(values["miner_allocation_not_preminted_units"],
                         90_000_000 * 100_000_000)

    def test_missing_real_company_address_or_timestamp_blocks(self):
        for field, value in (("public_address",None),("public_address","invalid")):
            proposal=copy.deepcopy(self.proposal)
            proposal["company_treasury"][field]=value
            with self.assertRaises(GenesisInputError):
                construct_inputs(proposal)
        for bad in (None, 0, False, "1801411200000"):
            proposal=copy.deepcopy(self.proposal)
            proposal["genesis_timestamp_ms"]=bad
            with self.assertRaises(GenesisInputError):
                construct_inputs(proposal)

    def test_rejects_supply_mismatch_test_premine_or_wrong_pot(self):
        for name, value in (("max_supply_units", 100_000_000_000_000_001),
                            ("mining_allocation_units", 1),
                            ("base_units_per_coin", 1_000_000_000_000),
                            ("initial_balances", [["Alice", 100]])):
            proposal=copy.deepcopy(self.proposal)
            proposal[name]=value
            with self.assertRaises(GenesisInputError):
                construct_inputs(proposal)
        proposal=copy.deepcopy(self.proposal)
        proposal["company_treasury"]["public_address"]=vesting_pot_ss58()
        with self.assertRaisesRegex(GenesisInputError,"vesting sovereign pot"):
            construct_inputs(proposal)

    def test_repo_proposal_still_rejected(self):
        p=json.loads((PROJECT/"config/genesis-proposal.json").read_text())
        with self.assertRaises(GenesisInputError):
            construct_inputs(p)

if __name__=="__main__":
    unittest.main()
