import tempfile
import unittest
from pathlib import Path
from scripts.patch_zk_leaf_amount_v2 import patch

class ZkLeafAmountPatchTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        f = self.root / "wormhole/circuit/src/lib.rs"
        f.parent.mkdir(parents=True)
        f.write_text("pub mod zk_merkle_proof;\n")
    def test_real_circuit_gadget_contains_max_supply_constraint(self):
        patch(self.root)
        lib = (self.root / "wormhole/circuit/src/lib.rs").read_text()
        source = (self.root / "wormhole/circuit/src/devnira_v2_amount_circuit.rs").read_text()
        self.assertIn("pub mod devnira_v2_amount_circuit;", lib)
        self.assertIn("builder.range_check(amount, DVN_BITS)", source)
        self.assertIn("enforce_target_less_than_const(builder, amount, exclusive, DVN_BITS)", source)
        self.assertIn("for amount in [input, output_1, output_2]", source)
    def test_refuses_duplicate(self):
        patch(self.root)
        with self.assertRaisesRegex(ValueError, "already applied"):
            patch(self.root)
    def test_refuses_changed_upstream(self):
        (self.root / "wormhole/circuit/src/lib.rs").write_text("upstream change\n")
        with self.assertRaisesRegex(ValueError, "changed"):
            patch(self.root)
if __name__ == "__main__":
    unittest.main()
