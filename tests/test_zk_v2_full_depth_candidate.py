import tempfile
import unittest
from pathlib import Path
from scripts.patch_zk_v2_full_depth_candidate import patch,MARKER

class VariableDepthNativeProofTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        path=self.root/"wormhole/circuit/src/devnira_v2_amount_circuit.rs"
        path.parent.mkdir(parents=True)
        path.write_text("pub const DVN_NATIVE_MAX:u64=10_000_000_000_000_000;\n"
                        "pub fn constrain_native_dvn_authenticated_spend() {}\n"
                        "pub fn constrain_native_dvn_value_conservation() {}\n")
        self.path=path

    def test_actual_multi_level_poseidon_constraints_staged(self):
        original=self.path.read_text()
        patch(self.root)
        s=self.path.read_text()
        self.assertTrue(s.startswith(original))
        for term in (
            MARKER, "is_const_less_than(&mut b,level,depth,bits)",
            "enforce_target_less_than_const(&mut b,depth,layers+1,bits)",
            "b.connect(current.elements[i],root.elements[i])",
            "b.register_public_inputs(&nullifier.elements)",
            "children.sort_by_key(|child|digest_to_bytes(&child.elements))",
            "dvn_v2_full_depth_actual_membership_depth_one_and_two",
            "dvn_v2_full_depth_rejects_wrong_root_wrong_sibling_domain_or_amount",
            "assert_eq!(data.common.num_public_inputs,15)",
        ):
            self.assertIn(term,s)

    def test_no_double_apply_and_missing_native_proof_fails_closed(self):
        patch(self.root)
        with self.assertRaisesRegex(ValueError,"already staged"):
            patch(self.root)
        self.path.write_text("pub const DVN_NATIVE_MAX:u64=10_000_000_000_000_000;")
        with self.assertRaisesRegex(ValueError,"Unsafe missing"):
            patch(self.root)

if __name__=="__main__":
    unittest.main()
