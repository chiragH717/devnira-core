import tempfile
import unittest
from pathlib import Path
from scripts.patch_zk_tree_native_v2 import patch, MARKER

class V2LeafNativePatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        folder=self.root/"pallets/zk-tree/src"
        folder.mkdir(parents=True)
        (folder/"tree.rs").write_text("/// Hash 4 child hashes into a parent node hash.\n")
        (folder/"tests.rs").write_text("fn amount_leaf(amount: u128) {}\n")

    def test_exact_amount_commitment_and_oversupply_guards(self):
        patch(self.root)
        source=(self.root/"pallets/zk-tree/src/tree.rs").read_text()
        tests=(self.root/"pallets/zk-tree/src/tests.rs").read_text()
        self.assertIn(MARKER,source)
        self.assertIn("pub fn hash_leaf_native_v2",source)
        self.assertIn("if native_amount > DVN_NATIVE_MAX_BASE_UNITS_V2",source)
        self.assertIn("native_amount as u64",source)
        self.assertNotIn("AMOUNT_SCALE_DOWN_FACTOR",source)
        self.assertIn("dvn_native_v2_leaf_commits_every_eight_decimal_base_unit_exactly",tests)
        self.assertIn("dvn_native_v2_leaf_accepts_100m_cap_but_rejects_oversupply",tests)

    def test_reject_duplicate_patch(self):
        patch(self.root)
        with self.assertRaisesRegex(ValueError,"already patched"):
            patch(self.root)

    def test_fail_closed_on_source_drift(self):
        file=self.root/"pallets/zk-tree/src/tree.rs"
        file.write_text("new upstream signature")
        with self.assertRaisesRegex(ValueError,"Unexpected ZK tree"):
            patch(self.root)
        self.assertEqual(file.read_text(),"new upstream signature")

if __name__=="__main__":
    unittest.main()
