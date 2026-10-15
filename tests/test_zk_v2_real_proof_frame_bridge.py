"""Stage the actual proof->FRAME bridge fail-closed, without replacing FRAME proof checking."""
import tempfile
import unittest
from pathlib import Path
from scripts.patch_zk_v2_real_proof_frame_bridge import patch,MARKER

class TestAuthenticatedProofFrameBridge(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.lib=self.root/"pallets/wormhole/src/lib.rs"
        self.tests=self.root/"pallets/wormhole/src/tests.rs"
        self.lib.parent.mkdir(parents=True)
        self.lib.write_text("// DEVNIRA_V2_22_PI_PREFLIGHT_NO_SETTLEMENT\n")
        self.tests.write_text("// DEVNIRA_V2_PALLET_ABI_STORAGE_TESTS\n")

    def test_only_real_frame_preflight_source_can_be_bridged(self):
        patch(self.root)
        s=self.tests.read_text()
        for required in (MARKER,"DEVNIRA_REAL_PROOF_PIS_TXT",
                         "devnira_v2_leaf_chain_preflight(&pis)",
                         "UsedNullifiers::<Test>::insert(nullifier,true)",
                         "Balances::total_issuance()",
                         "changed[2]+=1","changed[16]^=1"):
            self.assertIn(required,s)
        with self.assertRaisesRegex(ValueError,"already staged"):
            patch(self.root)

    def test_missing_frame_abi_fails_without_edit(self):
        self.lib.write_text("unrelated V1 source")
        old=self.tests.read_bytes()
        with self.assertRaisesRegex(ValueError,"FRAME 22PI"):
            patch(self.root)
        self.assertEqual(old,self.tests.read_bytes())

    def test_missing_real_frame_history_tests_fails_without_edit(self):
        self.tests.write_text("not a tested FRAME pallet")
        old=self.tests.read_bytes()
        with self.assertRaisesRegex(ValueError,"history/replay"):
            patch(self.root)
        self.assertEqual(old,self.tests.read_bytes())

if __name__=="__main__":
    unittest.main()
