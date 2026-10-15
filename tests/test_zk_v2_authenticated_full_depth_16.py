import tempfile
import unittest
from pathlib import Path
from scripts.patch_zk_v2_authenticated_full_depth_16 import patch, MARKER, MAX_DEPTH
from scripts.patch_zk_v2_authentic_22pi_leaf import RUST as AUTH
from scripts.patch_zk_v2_multilevel_authentic_22pi import patch as multilevel

class FullDepthAuthenticated22PiTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.source=self.root/"wormhole/circuit/src/devnira_v2_amount_circuit.rs"
        self.source.parent.mkdir(parents=True)
        self.source.write_text("pub const DVN_NATIVE_MAX:u64=1;\n"+AUTH)
        self.upstream=self.root/"common/src/zk_merkle.rs"
        self.upstream.parent.mkdir(parents=True)
        self.upstream.write_text("pub const MAX_DEPTH: usize = 16;")
    def test_exact_source_and_16_layer_adversarial_tests(self):
        multilevel(self.root)
        patch(self.root)
        code=self.source.read_text()
        self.assertEqual(MAX_DEPTH,16)
        for needle in (MARKER,"assert!((1..=16).contains(&layers)",
                       "dvn_v2_full_leaf_22pi_canonical_max_depth_16_real_proof",
                       "dvn_v2_full_leaf_22pi_full_depth_wrong_sibling_position_and_root_rejected",
                       "dvn_v2_full_leaf_22pi_refuses_empty_or_17_depth_before_build",
                       "BlockHeader::conditional_block_hash_binding(",
                       "Nullifier::conditional_hash_binding(",
                       "enforce_target_less_than_const(&mut b,remainder,10_000,14)"):
            self.assertIn(needle,code)
        with self.assertRaisesRegex(ValueError,"already staged"):
            patch(self.root)
    def test_upstream_depth_change_rejected_without_edit(self):
        multilevel(self.root)
        before=self.source.read_bytes()
        self.upstream.write_text("pub const MAX_DEPTH: usize = 15;")
        with self.assertRaisesRegex(ValueError,"MAX_DEPTH changed"):
            patch(self.root)
        self.assertEqual(before,self.source.read_bytes())
    def test_no_activation_without_authenticated_merkle(self):
        before=self.source.read_bytes()
        with self.assertRaisesRegex(ValueError,"missing canonical source"):
            patch(self.root)
        self.assertEqual(before,self.source.read_bytes())
if __name__=="__main__":
    unittest.main()
