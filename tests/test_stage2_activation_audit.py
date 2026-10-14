import json
import tempfile
import unittest
from pathlib import Path

from scripts.stage2_activation_audit import check, ZK_PROOF_CRATES

class ActivationAuditTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        self.files = {
            "runtime/src/lib.rs": "",
            "Cargo.toml": "",
            "pallets/zk-tree/src/tree.rs": "",
            "pallets/wormhole/src/lib.rs": "",
            "runtime/src/configs/mod.rs": "",
            "node/src/chain_spec.rs": "",
            "runtime/src/genesis_config_presets/mod.rs": "",
        }
        for path, content in self.files.items():
            out = self.root / path
            out.parent.mkdir(parents=True,exist_ok=True)
            out.write_text(content)

    def write(self, path, content):
        (self.root/path).write_text(content)

    def test_original_quantus_v1_stays_blocked(self):
        self.write("runtime/src/lib.rs",
                   "pub const UNIT: Balance = 1_000_000_000_000;")
        self.write("Cargo.toml","\n".join(
            f'{crate} = {{ version = "=4.3.0" }}' for crate in ZK_PROOF_CRATES))
        self.write("pallets/zk-tree/src/tree.rs",
                   "pub const AMOUNT_SCALE_DOWN_FACTOR: u128 = 10_000_000_000;")
        self.write("pallets/wormhole/src/lib.rs",
                   "pub const SCALE_DOWN_FACTOR: u128 = 10_000_000_000;")
        result=check(self.root,{"company_treasury":{"public_address":None},
                                "genesis_timestamp_ms":None})
        self.assertFalse(result["checks"]["native_runtime_8_decimals"])
        self.assertFalse(result["checks"]["legacy_quantized_leaf_removed"])
        self.assertFalse(result["checks"]["active_wormhole_v2_batch_parser"])
        self.assertFalse(result["active_v2_integration_proven"])
        self.assertGreaterEqual(len(result["missing"]),10)

    def test_adding_opt_in_v2_leaf_does_not_mean_active(self):
        self.write("pallets/zk-tree/src/tree.rs",
                   "fn get_leaf_hash<T: Config>(i:u64)-> Hash256 { hash_leaf::<T>(&leaf) }\n"
                   "fn hash_leaf_native_v2<T: Config>(leaf: &ZkLeaf)-> Result<Hash256, &str> { todo!() }")
        result=check(self.root,{})
        self.assertFalse(result["checks"]["native_v2_leaf_selected_by_active_tree"])
        self.assertFalse(result["checks"]["active_wormhole_v2_verifier_artifacts"])

    def test_partial_runtime_changes_never_activate_proofs(self):
        self.write("runtime/src/lib.rs",
                   "pub const UNIT: Balance = 100_000_000;\n"
                   "pub const MAX_SUPPLY: Balance = 100_000_000 * UNIT;")
        self.write("Cargo.toml","\n".join(
            f'{crate} = {{ version = "=4.4.0" }}' for crate in ZK_PROOF_CRATES))
        result=check(self.root,{"company_treasury":{"public_address":"public-only"},
                                "genesis_timestamp_ms":1801411200000})
        self.assertTrue(result["checks"]["native_runtime_8_decimals"])
        self.assertTrue(result["checks"]["runtime_100m_supply_cap"])
        self.assertFalse(result["checks"]["active_wormhole_v2_batch_parser"])
        self.assertFalse(result["checks"]["genesis_has_actual_runtime_allocation"])

if __name__=="__main__":
    unittest.main()
