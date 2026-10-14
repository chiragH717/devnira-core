"""Regression checks for real native Dilithium87 custody signing CLI injection."""
import tempfile
import unittest
from pathlib import Path

from scripts.patch_dvn_custody_signing import patch


class DevniraNativeCustodySigningPatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        folder=self.root/"node/src"
        folder.mkdir(parents=True)
        self.cli=folder/"cli.rs"
        self.command=folder/"command.rs"
        self.cli.write_text(
            "pub enum QuantusKeySubcommand {\n\tDevnira {\n a: u32\n},\n}\n"
        )
        self.command.write_text(
            "use qp_dilithium_crypto::{traits::WormholeAddress, Dilithium87Pair};\n"
            "/// Parse and run command line arguments\n"
            "fn run() { match cmd {\nQuantusKeySubcommand::Devnira { a } => {},\n} }\n"
        )

    def test_adds_real_sign_verify_commands_without_secret_argv(self):
        patch(self.root)
        cli=self.cli.read_text()
        code=self.command.read_text()
        self.assertIn('name = "devnira-sign"',cli)
        self.assertIn('name = "devnira-verify"',cli)
        self.assertIn("message: String",cli)
        self.assertIn("expected_address: String",cli)
        self.assertNotIn("mnemonic: String",cli)
        self.assertNotIn("suri: String",cli)
        self.assertIn("read_secret_from_stdin",code)
        self.assertIn("Dilithium87Pair::from_keypair",code)
        self.assertIn("Dilithium87Pair::verify",code)
        self.assertIn("let signature_bytes: &[u8] = signed.as_ref();",code)
        self.assertIn("hex::encode(signature_bytes)",code)
        self.assertNotIn("hex::encode(signed.as_ref())",code)
        self.assertIn('m/44\u0027/900190\u0027/{}\u0027/0\u0027/0\u0027',code)
        self.assertIn("signature.public() != public_key",code)
        self.assertIn("Ss58AddressFormat::custom(190)",code)
        self.assertIn("DEVNIRA-COMPANY-GENESIS-OWNERSHIP-V1",code)
        self.assertIn("devnira_native_signature_matches_ss58_190_hd_address",code)

    def test_double_application_fail_closed(self):
        patch(self.root)
        with self.assertRaisesRegex(ValueError,"already installed"):
            patch(self.root)

    def test_drift_does_not_mutate_either_source(self):
        self.command.write_text("source changed")
        before=self.cli.read_text()
        with self.assertRaisesRegex(ValueError,"source drift"):
            patch(self.root)
        self.assertEqual(self.cli.read_text(),before)
        self.assertEqual(self.command.read_text(),"source changed")


if __name__=="__main__":
    unittest.main()
