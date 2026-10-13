import tempfile
import unittest
from pathlib import Path
from scripts.patch_zk_amount_v2 import patch

class PatchZkAmountV2Tests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        path = self.root / "pallets/zk-tree/src/lib.rs"
        path.parent.mkdir(parents=True)
        path.write_text('#![cfg_attr(not(feature = "std"), no_std)]\npub mod tree;\n')

    def test_registers_real_pallet_module(self):
        patch(self.root)
        lib = (self.root / "pallets/zk-tree/src/lib.rs").read_text()
        rust = (self.root / "pallets/zk-tree/src/devnira_amount.rs").read_text()
        self.assertIn("pub mod devnira_amount;", lib)
        self.assertIn("fn dvn_native_felt_roundtrip()", rust)
        self.assertNotIn("AMOUNT_SCALE_DOWN_FACTOR =", rust)
        self.assertIn("Prototype only", rust)

    def test_rejects_second_application(self):
        patch(self.root)
        with self.assertRaisesRegex(ValueError, "already applied"):
            patch(self.root)

    def test_fails_closed_on_upstream_drift(self):
        (self.root / "pallets/zk-tree/src/lib.rs").write_text("changed")
        with self.assertRaisesRegex(ValueError, "upstream changed"):
            patch(self.root)

if __name__ == "__main__":
    unittest.main()
