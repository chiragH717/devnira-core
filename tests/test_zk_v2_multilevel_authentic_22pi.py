import tempfile
import unittest
from pathlib import Path
from scripts.patch_zk_v2_multilevel_authentic_22pi import patch, MARKER
from scripts.patch_zk_v2_authentic_22pi_leaf import RUST

class CanonicalFullSpendDepthTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.source=self.root/"wormhole/circuit/src/devnira_v2_amount_circuit.rs"
        self.source.parent.mkdir(parents=True)
        self.source.write_text("pub const DVN_NATIVE_MAX:u64=1;\n"+RUST)
    def test_original_22pi_owner_is_one_multilevel_proof(self):
        patch(self.root)
        s=self.source.read_text()
        for token in (MARKER,
            "fn build(layers:usize)",
            "for _level in 0..layers",
            "b.connect(computed_root.elements[i],committed_root.elements[i])",
            "BlockHeader::conditional_block_hash_binding",
            "Nullifier::conditional_hash_binding",
            "enforce_target_less_than_const(&mut b,remainder,10_000,14)",
            "dvn_v2_full_leaf_22pi_one_and_three_levels_have_unchanged_pi",
            "dvn_v2_full_leaf_22pi_rejects_wrong_deep_sibling_and_position",
            "let (data,t)=build(2)"):
            self.assertIn(token,s)
        with self.assertRaisesRegex(ValueError,"already staged"):
            patch(self.root)
    def test_original_one_level_auth_proof_required_and_atomic_failure(self):
        self.source.write_text("other crypto proof")
        before=self.source.read_bytes()
        with self.assertRaisesRegex(ValueError,"auth.*22PI proof missing"):
            patch(self.root)
        self.assertEqual(self.source.read_bytes(),before)
    def test_truncated_header_merkle_binding_refused(self):
        self.source.write_text(self.source.read_text().replace(
            "        let committed_root=b.add_virtual_hash();",""))
        before=self.source.read_bytes()
        with self.assertRaisesRegex(ValueError,"anchored Merkle"):
            patch(self.root)
        self.assertEqual(self.source.read_bytes(),before)
if __name__=="__main__":
    unittest.main()
