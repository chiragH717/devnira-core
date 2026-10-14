import hashlib
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from spec.ss58_company_account import encode_ss58_account
from spec.verify_company_custody import (
    issue_challenge, verify_company_certificate, UnverifiedCustody,
)

ADDR=encode_ss58_account(bytes(range(1,33)))
OTHER=encode_ss58_account(bytes([21]*32))
NOW=datetime(2027,1,30,12,tzinfo=timezone.utc)
SHA256=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()

class CompanyCustodyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.node=Path(self.tmp.name)/"trusted-devnira-node"
        self.node.write_bytes(b"TEST ONLY - NOT A REAL NODE")
        self.digest=SHA256(self.node)
        self.challenge=issue_challenge(ADDR,now=NOW)
        self.certificate={**self.challenge,
            "public_key_hex":"0x"+"a1"*32,
            "signature_hex":"0x"+"b2"*100}

    def test_strong_domain_bound_fresh_challenge(self):
        self.assertEqual(len(self.challenge["nonce"]),64)
        self.assertIn("devnira-mainnet-v1",self.challenge["message"])
        self.assertIn(ADDR,self.challenge["message"])
        with self.assertRaises(UnverifiedCustody):
            issue_challenge(encode_ss58_account(bytes(range(1,33)),prefix=189),now=NOW)

    @patch("spec.verify_company_custody._run_native")
    def test_native_crypto_signature_and_public_account_both_required(self, native):
        native.side_effect=["Signature verifies correctly.\n",
            '{"ss58Address": "'+ADDR+'"}']
        result=verify_company_certificate(self.certificate,self.node,self.digest,now=NOW)
        self.assertEqual(result["company_address"],ADDR)
        self.assertTrue(result["ownership_signature_verified"])
        self.assertEqual(native.call_count,2)
        self.assertEqual(native.call_args_list[0].args[1],"verify")
        self.assertEqual(native.call_args_list[1].args[1],"inspect")

    @patch("spec.verify_company_custody._run_native")
    def test_public_key_not_bound_to_company_address_rejected(self, native):
        native.side_effect=["Signature verifies correctly.\n",
            '{"ss58Address": "'+OTHER+'"}']
        with self.assertRaisesRegex(UnverifiedCustody,"does not derive"):
            verify_company_certificate(self.certificate,self.node,self.digest,now=NOW)

    @patch("spec.verify_company_custody._run_native")
    def test_expired_or_changed_message_rejected_before_native_verifier(self,native):
        for bad in [
            dict(self.certificate, message="wrong"),
            dict(self.certificate, company_address=OTHER),
            dict(self.certificate, nonce="0"*64),
        ]:
            with self.assertRaises(UnverifiedCustody):
                verify_company_certificate(bad,self.node,self.digest,now=NOW)
        with self.assertRaisesRegex(UnverifiedCustody,"expired"):
            verify_company_certificate(self.certificate,self.node,self.digest,
                                       now=NOW+timedelta(hours=25))
        native.assert_not_called()

    @patch("spec.verify_company_custody._run_native")
    def test_verifier_binary_is_pinned_not_caller_selected(self,native):
        with self.assertRaisesRegex(UnverifiedCustody,"trusted build"):
            verify_company_certificate(self.certificate,self.node,"f"*64,now=NOW)
        native.assert_not_called()

    @patch("spec.verify_company_custody._run_native")
    def test_invalid_crypto_signature_fails_closed(self,native):
        native.side_effect=UnverifiedCustody("Native DEVNIRA signature/address verification failed")
        with self.assertRaises(UnverifiedCustody):
            verify_company_certificate(self.certificate,self.node,self.digest,now=NOW)

if __name__=="__main__":
    unittest.main()
