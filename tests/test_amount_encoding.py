import tempfile
import unittest
from pathlib import Path
from scripts.audit_amount_encoding import check

class EncodingTests(unittest.TestCase):
    def write(self, root, unit, quantum):
        (root / "runtime/src").mkdir(parents=True)
        (root / "pallets/zk-tree/src").mkdir(parents=True)
        (root / "runtime/src/lib.rs").write_text(f"pub const UNIT: Balance = {unit};")
        (root / "pallets/zk-tree/src/tree.rs").write_text(f"pub const AMOUNT_SCALE_DOWN_FACTOR: u128 = {quantum};")
    def test_upstream_quantus_is_incompatible(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            self.write(root, "1_000_000_000_000", "10_000_000_000")
            with self.assertRaisesRegex(ValueError, "STOP"):
                check(root)
    def test_unit_change_without_circuit_migration_fails(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            self.write(root, "100_000_000", "10_000_000_000")
            with self.assertRaisesRegex(ValueError, "ZK leaf quantum"):
                check(root)
    def test_compatible_arithmetic_only(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            self.write(root, "100_000_000", "1_000_000")
            check(root)

if __name__ == "__main__":
    unittest.main()
