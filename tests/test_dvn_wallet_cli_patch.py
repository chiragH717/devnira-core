"""DEVNIRA offline Dilithium company keygen integration source tests.

Synthetic Rust fixtures mirror upstream node CLI anchors; full native compile
is a separate GitHub Actions job using pinned Quantus revision.
"""
import tempfile
import unittest
from pathlib import Path
from scripts.patch_dvn_wallet_cli import patch, DVN_STANDARD_HD_COIN_TYPE, DVN_WORMHOLE_HD_COIN_TYPE

class DevniraWalletCliPatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        node=self.root/"node/src"
        node.mkdir(parents=True)
        cmd="""SensitiveBytes64, QUANTUS_DILITHIUM_CHAIN_ID,
    QUANTUS_WORMHOLE_CHAIN_ID,
};
use zeroize::{Zeroize, Zeroizing};
"""
        cmd=cmd.replace("    QUANTUS_WORMHOLE_CHAIN_ID,", "\tQUANTUS_WORMHOLE_CHAIN_ID,")
        cmd+=('let a=QUANTUS_DILITHIUM_CHAIN_ID; let b=QUANTUS_DILITHIUM_CHAIN_ID;'
              ' let c=QUANTUS_DILITHIUM_CHAIN_ID;\n')
        cmd+=('let a=QUANTUS_WORMHOLE_CHAIN_ID; let b=QUANTUS_WORMHOLE_CHAIN_ID;'
              ' let c=QUANTUS_WORMHOLE_CHAIN_ID;\n')
        cmd+=('Ss58AddressFormat::custom(189)\n'*5)
        cmd+='QuantusKeySubcommand::Quantus {\n'
        cmd+='\t\t\t\t} => {\n\t\t\t\t\t// Secrets are read from stdin, never from argv (see cli.rs).\n'
        cmd+='Generating Quantus Standard address...\nGenerating wormhole address...\n'
        cmd+='XXXXXXXXXXXXXXX Quantus Account Details\nXXXXXXXXXXXXXXX Quantus Wormhole Details\n'
        self.cli=node/"cli.rs"
        self.command=node/"command.rs"
        self.cli.write_text("\tQuantus {\n")
        self.command.write_text(cmd)

    def test_correct_hd_network_keys_and_terminal_guard(self):
        patch(self.root)
        code=self.command.read_text()
        self.assertIn('const DEVNIRA_STANDARD_HD_COIN_TYPE: &str = "900190\'";',code)
        self.assertIn('const DEVNIRA_WORMHOLE_HD_COIN_TYPE: &str = "900191\'";',code)
        self.assertIn("is_terminal()",code)
        self.assertIn("custom(190)",code)
        self.assertNotIn("custom(189)",code)
        self.assertNotIn("QUANTUS_DILITHIUM_CHAIN_ID",code)
        self.assertIn("QuantusKeySubcommand::Devnira",code)
        self.assertIn("\tDevnira {",self.cli.read_text())
        self.assertEqual(DVN_STANDARD_HD_COIN_TYPE,"900190'")
        self.assertEqual(DVN_WORMHOLE_HD_COIN_TYPE,"900191'")

    def test_fail_closed_when_patched_twice(self):
        patch(self.root)
        with self.assertRaisesRegex(ValueError,"source drift"):
            patch(self.root)

    def test_rejects_drift_without_partial_change(self):
        before=self.command.read_text().replace("custom(189)","custom(190)",1)
        self.command.write_text(before)
        with self.assertRaisesRegex(ValueError,"source drift"):
            patch(self.root)
        self.assertEqual(self.command.read_text(),before)
        self.assertEqual(self.cli.read_text(),"\tQuantus {\n")

if __name__=="__main__":
    unittest.main()
