import tempfile
import unittest
from pathlib import Path
from scripts.patch_dvn_runtime_units import patch

RUNTIME = (
    'spec_name: alloc::borrow::Cow::Borrowed("quantus-runtime"),\n'
    'impl_name: alloc::borrow::Cow::Borrowed("quantus-runtime"),\n'
    'pub const UNIT: Balance = 1_000_000_000_000;\n'
    'pub const MILLI_UNIT: Balance = 1_000_000_000;\n'
    'pub const MICRO_UNIT: Balance = 1_000_000;\n'
    'pub const MAX_SUPPLY: Balance = 21_000_000 * UNIT;\n'
)

class RuntimeUnitMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        files = {
            "Cargo.toml": "\n".join(
                f'{crate} = {{ version = "=4.4.0", default-features = false }}'
                for crate in ("qp-wormhole-circuit", "qp-wormhole-inputs",
                              "qp-wormhole-prover", "qp-wormhole-verifier",
                              "qp-wormhole-aggregator", "qp-zk-circuits-common")
            ),
            "runtime/src/lib.rs": RUNTIME,
            "runtime/src/configs/mod.rs": "type MiningCap = ConstU128<{ 90_000_000 * UNIT }>;",
            "pallets/zk-tree/src/tree.rs": "V2 no scaling",
            "pallets/wormhole/src/lib.rs": "V2 wormhole",
            "pallets/vesting/src/lib.rs": "ImmutableGenesisScheduleCount",
        }
        for name, data in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(data)

    def test_fails_closed_for_quantus_v1_leaf_without_mutating_runtime(self):
        (self.root / "pallets/zk-tree/src/tree.rs").write_text(
            "pub const AMOUNT_SCALE_DOWN_FACTOR: u128 = 10_000_000_000;")
        with self.assertRaisesRegex(ValueError, "V1 12-decimal scaling"):
            patch(self.root)
        self.assertEqual((self.root / "runtime/src/lib.rs").read_text(), RUNTIME)

    def test_fails_closed_for_quantus_v1_wormhole(self):
        (self.root / "pallets/wormhole/src/lib.rs").write_text(
            "pub const SCALE_DOWN_FACTOR: u128 = 10_000_000_000;")
        with self.assertRaisesRegex(ValueError, "Wormhole V1"):
            patch(self.root)

    def test_fails_closed_for_u32_truncation(self):
        (self.root / "pallets/zk-tree/src/tree.rs").write_text(
            "u32::try_from(amount_u128 / AMOUNT_SCALE_DOWN_FACTOR)")
        with self.assertRaisesRegex(ValueError, "truncates/saturates"):
            patch(self.root)

    def test_fails_without_protected_genesis(self):
        (self.root / "pallets/vesting/src/lib.rs").write_text("")
        with self.assertRaisesRegex(ValueError, "protected founder"):
            patch(self.root)

    def test_blocks_old_v1_proof_crates_even_if_quantum_is_edited(self):
        cargo=self.root/"Cargo.toml"
        cargo.write_text(cargo.read_text().replace('=4.4.0','=4.3.0'))
        with self.assertRaisesRegex(ValueError,"Quantus V1 4.3.0"):
            patch(self.root)
        self.assertEqual((self.root/"runtime/src/lib.rs").read_text(),RUNTIME)

    def test_missing_verifier_proof_version_is_unsafe(self):
        cargo=self.root/"Cargo.toml"
        cargo.write_text(cargo.read_text().replace("qp-wormhole-verifier",
                                                  "removed-verifier"))
        with self.assertRaisesRegex(ValueError,"pinned proof version"):
            patch(self.root)
        self.assertEqual((self.root/"runtime/src/lib.rs").read_text(),RUNTIME)

    def test_stages_eight_decimal_runtime_when_local_guards_satisfied(self):
        patch(self.root)
        code = (self.root / "runtime/src/lib.rs").read_text()
        self.assertIn("pub const UNIT: Balance = 100_000_000;", code)
        self.assertIn("pub const MILLI_UNIT: Balance = 100_000;", code)
        self.assertIn("pub const MICRO_UNIT: Balance = 100;", code)
        self.assertIn("pub const MAX_SUPPLY: Balance = 100_000_000 * UNIT;", code)
        self.assertEqual(code.count('"devnira-runtime"'), 2)
        with self.assertRaisesRegex(ValueError, "previously patched"):
            patch(self.root)

if __name__ == "__main__":
    unittest.main()
