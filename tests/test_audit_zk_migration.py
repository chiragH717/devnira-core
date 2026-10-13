import tempfile
import unittest
from pathlib import Path
from scripts.audit_zk_migration import audit

class ZkMigrationAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for file in [
            "runtime/src/lib.rs",
            "pallets/zk-tree/src/tree.rs",
            "pallets/wormhole/src/lib.rs",
            "runtime/src/configs/mod.rs",
            "Cargo.toml",
        ]:
            path = self.root / file
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("")
    def write(self, path, text):
        (self.root / path).write_text(text)
    def test_upstream_v1_is_blocked_at_every_layer(self):
        self.write("runtime/src/lib.rs", "pub const UNIT: Balance = 1_000_000_000_000;\npub const MAX_SUPPLY: Balance = 21_000_000 * UNIT;")
        self.write("pallets/zk-tree/src/tree.rs", (
            "pub const AMOUNT_SCALE_DOWN_FACTOR: u128 = 10_000_000_000;\n"
            "u32::try_from(amount_u128 / AMOUNT_SCALE_DOWN_FACTOR).unwrap_or(u32::MAX);\n"
            "let amount_quantized = 0;"
        ))
        self.write("pallets/wormhole/src/lib.rs", "pub const SCALE_DOWN_FACTOR: u128 = 10_000_000_000;")
        self.write("runtime/src/configs/mod.rs", "pub const VestingPayoutQuantum: Balance = pallet_wormhole::SCALE_DOWN_FACTOR;")
        self.write("Cargo.toml", "".join(
            f'{name} = {{ version = "=4.3.0", default-features = false }}\n'
            for name in ("qp-wormhole-circuit", "qp-wormhole-inputs", "qp-wormhole-prover", "qp-wormhole-verifier")
        ))
        result = audit(self.root)
        self.assertFalse(result["passed"])
        self.assertTrue(any("runtime UNIT" in x for x in result["errors"]))
        self.assertTrue(any("ZK-tree still" in x for x in result["errors"]))
        self.assertTrue(any("Wormhole still" in x for x in result["errors"]))
        self.assertEqual(sum("upstream V1" in x for x in result["errors"]), 4)

    def test_codec_alone_not_sufficient(self):
        self.write("runtime/src/lib.rs", "pub const UNIT: Balance = 100_000_000;\npub const MAX_SUPPLY: Balance = 100_000_000 * UNIT;")
        self.write("runtime/src/configs/mod.rs", "pub const VestingPayoutQuantum: Balance = pallet_wormhole::SCALE_DOWN_FACTOR;")
        result = audit(self.root)
        self.assertFalse(result["passed"])
        self.assertEqual(len([x for x in result["errors"] if "runtime UNIT" in x]), 0)
        self.assertTrue(any("circuit/proof migration" in x for x in result["errors"]))

if __name__ == "__main__":
    unittest.main()
