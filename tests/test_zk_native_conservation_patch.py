import tempfile
import unittest
from pathlib import Path
from scripts.patch_zk_native_conservation import patch, MARKER

class NativeDvnConservationPatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name)
        self.file=root/"wormhole/circuit/src/devnira_v2_amount_circuit.rs"
        self.file.parent.mkdir(parents=True)
        self.file.write_text("pub const DVN_NATIVE_MAX: u64 = 10_000_000_000_000_000;\n"
                             "pub fn constrain_native_dvn_leaf_hash() {}\n")
        self.root=root

    def test_exact_conservation_and_invalid_witnesses(self):
        patch(self.root)
        s=self.file.read_text()
        self.assertIn(MARKER,s)
        self.assertIn("builder.connect(input, outputs_and_fee)",s)
        self.assertIn("constrain_native_dvn_authenticated_spend",s)
        self.assertIn("dvn_native_authenticated_leaf_and_public_outputs_are_bound",s)
        self.assertIn("builder.register_public_input(first)",s)
        self.assertIn("builder.register_public_input(change)",s)
        self.assertIn("builder.register_public_input(fee)",s)
        self.assertIn("3 * DVN_NATIVE_MAX < GOLDILOCKS",s)
        self.assertIn("(DVN_NATIVE_MAX,DVN_NATIVE_MAX,1,0)",s)
        self.assertIn("(DVN_NATIVE_MAX, DVN_NATIVE_MAX + 1,0,0)",s)

    def test_reapplication_rejected(self):
        patch(self.root)
        with self.assertRaisesRegex(ValueError,"already installed"):
            patch(self.root)

    def test_fail_closed_on_upstream_drift(self):
        self.file.write_text("v3 source")
        with self.assertRaisesRegex(ValueError,"Missing V2"):
            patch(self.root)
        self.assertEqual(self.file.read_text(),"v3 source")

if __name__=="__main__":
    unittest.main()
