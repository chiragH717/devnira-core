"""Source composition gate; actual 4-ary Poseidon checks are Rust FRAME tests."""
import tempfile
import unittest
from pathlib import Path
from scripts.patch_zk_v2_custody_merkle_depth16 import patch,MARKER,HISTORY_MARKER
class V2Depth16CompositionTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        wd=self.root/"pallets/wormhole/src"
        wd.mkdir(parents=True)
        self.lib=wd/"lib.rs"
        self.tests=wd/"tests.rs"
        self.lib.write_text(
            "DEVNIRA_V2_CUSTODY_COMMITMENTS_STORAGE_NO_FINALIZED_ROOT\n"
            "\t#[pallet::hooks]\n\timpl<T: Config> Hooks<BlockNumberFor<T>> for Pallet<T> {\n"
            "\t\tfn on_initialize(n: BlockNumberFor<T>) -> Weight {\n"
            "    pub type DvnV2EscrowCommitment<T:Config>=\n"
            "        StorageMap<_,Twox64Concat,u64,[u8;32],OptionQuery>;\n"
            "        /// DEVNIRA_V2_NATIVE_ESCROW_BACKING_INTERNAL_NO_DISPATCH\n"
            "                    DvnV2EscrowCommitment::<T>::insert(id,commitment);\n")
        self.tests.write_text(
            "// DEVNIRA_V2_NATIVE_ESCROW_CUSTODY_NATIVE_FRAME_TESTS\n"
            "    use crate::pallet::{DvnV2EscrowRecipientCount,DvnV2EscrowReceipt,"
            "DvnV2EscrowCommitment};\n"
            "    #[test]\n"
            "    fn dvn_v2_deposit_bad_alias_zero_overflow_vault_and_failed_debit_reject(){\n")
    def test_depth16_atomic_and_nonheader(self):
        patch(self.root)
        lib=self.lib.read_text()
        rust_tests=self.tests.read_text()
        for part in (MARKER,HISTORY_MARKER,"const DEPTH:u8=16",
                     "const MAX_LEAVES:u64=1u64<<32",
                     "DvnV2TreeCount::<T>::get()",
                     "pallet_zk_tree::tree::hash_node(&children)",
                     "Self::devnira_v2_append_merkle_internal(id,commitment)?;",
                     "DvnV2TreeDirty::<T>::take()",
                     "DvnV2TreeHistory::<T>::insert("):
            self.assertIn(part,lib)
        self.assertIn("dvn_v2_deposit_fixed_depth16_merkle_root_independent_of_v1",rust_tests)
        self.assertIn("dvn_v2_deposit_current_witness_16_levels_and_tamper_detection",rust_tests)
        self.assertIn("dvn_v2_deposit_failure_cannot_advance_tree_or_snapshot",rust_tests)
        self.assertNotIn("set_zk_tree_root",lib)
        with self.assertRaisesRegex(ValueError,"already installed"):
            patch(self.root)
    def test_upstream_anchor_drift_is_atomic(self):
        for file,needle in [
            (self.lib,"DvnV2EscrowCommitment::<T>::insert(id,commitment);"),
            (self.lib,"fn on_initialize(n: BlockNumberFor<T>) -> Weight {"),
            (self.tests,"DvnV2EscrowReceipt,DvnV2EscrowCommitment};")
        ]:
            old=file.read_text()
            file.write_text(old.replace(needle,"UNEXPECTED_UPSTREAM_CHANGE"))
            before=(self.lib.read_text(),self.tests.read_text())
            with self.assertRaisesRegex(ValueError,"STOP"):
                patch(self.root)
            self.assertEqual(before,(self.lib.read_text(),self.tests.read_text()))
            file.write_text(old)
if __name__=="__main__":
    unittest.main()
