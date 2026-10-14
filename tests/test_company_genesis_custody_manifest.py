import hashlib
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from scripts.prepare_company_genesis_custody import build_signed_company_manifest, write_fresh
from spec.genesis_allocations import INSTANT_BUDGET, VESTED_BUDGET
from spec.ss58_company_account import encode_ss58_account

ADDR=encode_ss58_account(bytes(range(1,33)))
GENESIS=datetime(2027,2,28,12,tzinfo=timezone.utc)

class SignedCompanyManifestTests(unittest.TestCase):
    @patch("scripts.prepare_company_genesis_custody.verify_company_certificate")
    def test_proven_company_owner_is_single_3m_7m_beneficiary(self, verifier):
        verifier.return_value={
            "company_address":ADDR,
            "verifier_sha256":"b"*64,
            "public_key_hex":"0x"+"f"*64,
            "ownership_signature_verified":True,
        }
        manifest=build_signed_company_manifest(
            {"public":"example"},Path("/not-used-in-unit-test"),"b"*64,GENESIS)
        self.assertTrue(manifest["company_address_verified"])
        self.assertFalse(manifest["production_genesis"])
        self.assertEqual(manifest["beneficiary_policy"],"single_company_treasury")
        self.assertEqual(manifest["beneficiaries"][0]["public_address"],ADDR)
        self.assertEqual(manifest["instant_total_units"],INSTANT_BUDGET)
        self.assertEqual(manifest["locked_total_units"],VESTED_BUDGET)
        self.assertEqual(len(manifest["monthly_unlocks"]),12)
        self.assertEqual(sum(x["amount_units"] for x in manifest["monthly_unlocks"]),VESTED_BUDGET)
        self.assertTrue(manifest["company_address_ownership_evidence"]["signed_challenge_verified"])

    @patch("scripts.prepare_company_genesis_custody.verify_company_certificate")
    def test_no_manifest_if_signature_is_unverified(self,verifier):
        verifier.side_effect=ValueError("Invalid signature")
        with self.assertRaises(ValueError):
            build_signed_company_manifest({},Path("untrusted"),"b"*64,GENESIS)

    def test_output_refuses_to_overwrite_ownership_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/"public-ownership.json"
            write_fresh(dest,{"public":True})
            with self.assertRaises(FileExistsError):
                write_fresh(dest,{"changed":True})
            self.assertIn('"public": true',dest.read_text())

if __name__=="__main__":
    unittest.main()
