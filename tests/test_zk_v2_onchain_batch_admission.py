import tempfile
import unittest
from pathlib import Path
from scripts.patch_zk_v2_onchain_batch_admission import patch, MARKER, TEST_MARKER

class ActualFrameBatchPreflightTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        src=self.root/"pallets/wormhole/src/lib.rs"
        src.parent.mkdir(parents=True)
        src.write_text("/// DEVNIRA_V2_22_PI_PREFLIGHT_NO_SETTLEMENT\n"+
            "pub(crate) fn devnira_v2_leaf_chain_preflight(x:u8){}\n"+
            "\t\tfn segment_is_inert(segment: &ExitSegment) -> bool { true }\n")
        (src.parent/"tests.rs").write_text("// historical tests\n")
        self.src=src
    def test_real_batch_guards_and_mock_state_tests(self):
        patch(self.root)
        body=self.src.read_text()
        tests=(self.src.parent/"tests.rs").read_text()
        for key in (MARKER,"batch.len() <= MAX_LEAVES",
                    "Self::devnira_v2_leaf_chain_preflight(pis)",
                    "earlier[4..8] != pis[4..8]",
                    "pis[16..21] == batch[0][16..21]",
                    "inputs <= DVN_MAX_NATIVE"):
            self.assertIn(key,body)
        for name in (TEST_MARKER,
            "dvn_v2_batch_real_storage_two_unique_spends_have_no_side_effects",
            "dvn_v2_batch_refuses_intrabatch_and_persisted_replay",
            "dvn_v2_batch_refuses_empty_oversized_cross_block_and_supply_cap"):
            self.assertIn(name,tests)
        with self.assertRaisesRegex(ValueError,"already applied"):
            patch(self.root)
    def test_base_onchain_preflight_missing_must_block_without_partial_changes(self):
        self.src.write_text("\t\tfn segment_is_inert(segment: &ExitSegment) -> bool {}")
        before=self.src.read_bytes()
        with self.assertRaisesRegex(ValueError,"single-leaf"):
            patch(self.root)
        self.assertEqual(self.src.read_bytes(),before)
if __name__=="__main__":
    unittest.main()
