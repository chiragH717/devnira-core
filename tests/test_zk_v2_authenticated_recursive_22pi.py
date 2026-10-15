"""Real source composition guards; GitHub Actions also runs actual Rust proofs."""
import tempfile
import unittest
from pathlib import Path
from scripts.patch_zk_v2_authentic_22pi_leaf import RUST as AUTH
from scripts.patch_zk_v2_multilevel_authentic_22pi import patch as multilevel
from scripts.patch_zk_v2_authenticated_full_depth_16 import patch as full_depth
from scripts.patch_zk_v2_authenticated_recursive_22pi import patch, MARKER

class FixedKey22PiComposition(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.source=self.root/"wormhole/circuit/src/devnira_v2_amount_circuit.rs"
        self.source.parent.mkdir(parents=True)
        self.source.write_text("pub const DVN_NATIVE_MAX:u64=10_000_000_000_000_000;\n"+AUTH)
        self.merkle=self.root/"common/src/zk_merkle.rs"
        self.merkle.parent.mkdir(parents=True)
        self.merkle.write_text("pub const MAX_DEPTH: usize = 16;")

    def test_only_authenticated_full_depth_22pi_can_be_wrapped(self):
        multilevel(self.root)
        full_depth(self.root)
        patch(self.root)
        source=self.source.read_text()
        for exact in (
            MARKER,
            "b.constant_verifier_data::<C>(&inner.verifier_only)",
            "b.verify_proof::<C>(&p,&vk,&inner.common)",
            "assert_eq!(inner.common.num_public_inputs,22",
            "dvn_v2_recursive22_real_full16_authenticated_leaf_fixed_vk",
            "dvn_v2_recursive22_two_distinct_real_nullifiers_aggregate_and_replay_fails",
            "dvn_v2_recursive22_rejects_same_abi_foreign_verifier_key",
            "f(if fault==\"next_count\"{2}else{1})",
            "enforce_target_less_than_const(",
            "assert_eq!(aggregate.public_inputs.len(),46)",
        ):
            self.assertIn(exact,source)
        with self.assertRaisesRegex(ValueError,"already staged"):
            patch(self.root)

    def test_no_partial_edit_on_version_skew(self):
        multilevel(self.root)
        full_depth(self.root)
        self.merkle.write_text("pub const MAX_DEPTH: usize = 15;")
        before=self.source.read_bytes()
        with self.assertRaisesRegex(ValueError,"MAX_DEPTH"):
            patch(self.root)
        self.assertEqual(before,self.source.read_bytes())

    def test_do_not_wrap_seven_pi_or_unbound_mock(self):
        before=self.source.read_bytes()
        with self.assertRaisesRegex(ValueError,"missing real authenticated"):
            patch(self.root)
        self.assertEqual(before,self.source.read_bytes())

if __name__=="__main__":
    unittest.main()
