import tempfile
import unittest
from pathlib import Path
from scripts.patch_zk_v2_aggregation_amounts import patch, MARKER

class V2AggregationPatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        base=self.root/"wormhole/aggregator/src"
        (base/"private_batch/circuit").mkdir(parents=True)
        (base/"public_batch/circuit").mkdir(parents=True)
        (base/"private_batch/circuit/circuit_logic.rs").write_text("real private batch fixture")
        (base/"public_batch/circuit/circuit_logic.rs").write_text("real public batch fixture")
        self.lib=base/"lib.rs"
        self.lib.write_text("pub mod private_batch;\npub mod public_batch;\n")
    def test_stages_real_private_and_public_proof_logic_without_legacy_change(self):
        old=self.lib.read_text()
        patch(self.root)
        source=(self.lib.parent/"devnira_v2_segment.rs").read_text()
        self.assertIn(MARKER,self.lib.read_text())
        self.assertTrue(self.lib.read_text().startswith(old))
        for piece in ("constrain_v2_private_batch_value",
                      "constrain_v2_public_batch_exits",
                      "enforce_target_less_than_const",
                      "builder.connect(total_in,plus_fee)",
                      "dvn_v2_private_batch_proves_exact_u64_fee_and_value_conservation",
                      "dvn_v2_public_batch_rejects_aggregate_above_native_supply"):
            self.assertIn(piece,source)
    def test_refuses_partial_or_repeat_patch(self):
        patch(self.root)
        with self.assertRaisesRegex(ValueError,"already exists"):
            patch(self.root)
    def test_source_drift_fails_before_mutation(self):
        self.lib.write_text("unknown")
        with self.assertRaisesRegex(ValueError,"Unrecognized"):
            patch(self.root)
        self.assertFalse((self.lib.parent/"devnira_v2_segment.rs").exists())
    def test_missing_recursive_wrapper_fails(self):
        (self.root/"wormhole/aggregator/src/private_batch/circuit/circuit_logic.rs").unlink()
        with self.assertRaisesRegex(ValueError,"private-batch"):
            patch(self.root)
if __name__=="__main__":
    unittest.main()
