"""Fail-closed source and fixture regression for cross-layer Poseidon2 golden tests."""
import tempfile
import unittest
from pathlib import Path
from scripts.patch_zk_native_hash_golden import patch, MARKER

class NativePoseidonGoldenPatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        folder=self.root/"wormhole/circuit/src"
        folder.mkdir(parents=True)
        (folder/"devnira_v2_amount_circuit.rs").write_text(
            "pub const DVN_NATIVE_MAX: u64 = 10_000_000_000_000_000;\n"
            "pub fn constrain_native_dvn_leaf_hash() {}\n"
        )
        (self.root/"wormhole/circuit/Cargo.toml").write_text(
            "[dependencies]\nqp-plonky2 = { workspace = true }\n"
        )

    def test_injects_six_cross_language_golden_vectors_and_same_poseidon_hash(self):
        patch(self.root)
        code=(self.root/"wormhole/circuit/src/devnira_v2_amount_circuit.rs").read_text()
        cargo=(self.root/"wormhole/circuit/Cargo.toml").read_text()
        self.assertIn(MARKER,code)
        self.assertIn("qp_poseidon_core::{Goldilocks, hash_to_bytes}",code)
        self.assertIn("builder.register_public_inputs(&hash.elements)",code)
        self.assertIn("58_333_333_333_333",code)
        self.assertIn("500_000_001",code)
        self.assertIn("DVN_NATIVE_MAX",code)
        self.assertIn("count >> 32",code)
        self.assertIn("qp-poseidon-core = { workspace = true }",cargo)

    def test_reapplication_fails_closed(self):
        patch(self.root)
        with self.assertRaisesRegex(ValueError,"already installed"):
            patch(self.root)

    def test_unexpected_circuit_changes_leave_source_unmodified(self):
        source=self.root/"wormhole/circuit/src/devnira_v2_amount_circuit.rs"
        source.write_text("broken source revision")
        with self.assertRaisesRegex(ValueError,"gadget missing"):
            patch(self.root)
        self.assertEqual(source.read_text(),"broken source revision")
        self.assertNotIn("qp-poseidon-core",(self.root/"wormhole/circuit/Cargo.toml").read_text())

if __name__=="__main__":
    unittest.main()
