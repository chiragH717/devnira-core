import tempfile
import unittest
from pathlib import Path
from scripts.patch_zk_v2_public_input_parser import patch, MARKER

class NativeV2ParserSourceTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root=Path(self.t.name)
        self.lib=self.root/"wormhole/inputs/src/lib.rs"
        self.lib.parent.mkdir(parents=True,exist_ok=True)
        self.original="\n".join((
            "pub struct PublicCircuitInputs",
            "pub output_amount_1: u32",
            "pub input_amount: u32",
            "pub struct PublicBatchPublicInputs",
            "pub const PUBLIC_INPUTS_FELTS_LEN: usize = 22;",
            "pub mod public_batch_pi",
            "fn hash_u64s_to_bytes_digest",
        ))+"\n"
        self.lib.write_text(self.original)

    def test_v2_is_added_without_modifying_v1_proof_parser(self):
        patch(self.root)
        mod=(self.lib.parent/"devnira_v2_public_inputs.rs").read_text()
        self.assertEqual(self.lib.read_text().split("// V2 opt-in parser only")[0],
                         self.original+"\n")
        self.assertIn(MARKER,self.lib.read_text())
        self.assertIn("pub input_amount: u64",mod)
        self.assertIn("pub output_amount_1: u64",mod)
        self.assertIn("pub struct DvnV2PrivateBatchPublicInputs",mod)
        self.assertIn("pub struct DvnV2PublicBatchPublicInputs",mod)
        self.assertIn("bound_aggregate_total",mod)
        self.assertIn("noncanonical Goldilocks",mod)
        self.assertIn("dvn_v2_leaf_preserves_full_precision_above_u32",mod)
        self.assertIn("dvn_v2_public_batch_u64_exits_are_not_u32",mod)
        self.assertIn("crate::PublicCircuitInputs::try_from_u64_slice",mod)

    def test_duplicate_patch_fails_closed(self):
        patch(self.root)
        with self.assertRaisesRegex(ValueError,"already installed"):
            patch(self.root)

    def test_partial_drift_leaves_files_untouched(self):
        self.lib.write_text("pub struct PublicCircuitInputs")
        with self.assertRaisesRegex(ValueError,"upstream V1 codec drift"):
            patch(self.root)
        self.assertFalse((self.lib.parent/"devnira_v2_public_inputs.rs").exists())

    def test_missing_directory_fails(self):
        self.lib.unlink()
        with self.assertRaises(FileNotFoundError):
            patch(self.root)

if __name__=="__main__":
    unittest.main()
