"""Composition guard only; GitHub also runs actual pinned FRAME Poseidon tests."""
import tempfile
import unittest
from pathlib import Path
from scripts.patch_zk_v2_native_custody_ledger import patch as custody_patch
from scripts.patch_zk_v2_custody_commitment import patch, TREE_MARKER, LEDGER_MARKER

class V2NativeCommitmentCompositionTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        zk=self.root/"pallets/zk-tree/src"
        worm=self.root/"pallets/wormhole/src"
        zk.mkdir(parents=True);worm.mkdir(parents=True)
        self.tree=zk/"tree.rs"
        self.tree.write_text("pub fn hash_leaf_native_v2<T: Config>(\n")
        self.lib=worm/"lib.rs"
        self.tests=worm/"tests.rs"
        self.lib.write_text(
            "pub(super) type UsedNullifiers<T: Config>\n"
            "type WormholeAccountId: Parameter\n"
            "pub fn verify_private_batch(\n"
            "\t#[pallet::event]\n"
            "\t#[pallet::generate_deposit(pub(super) fn deposit_event)]\n"
            "\t\tfn segment_is_inert(segment: &ExitSegment) -> bool {\n"
            "\t\t\t\tNone => {\n"
            "\t\t\t\t\tSelf::record_transfer(T::AssetId::default(), &from, &to, amount);\n"
            "\t\t\t\t\ttrue\n"
            "\t\t\t\t},\n")
        self.tests.write_text("// existing upstream tests\n")
        custody_patch(self.root)
    def test_exact_receipt_uses_real_native_leaf_and_atomic_balance_storage(self):
        patch(self.root)
        tree=self.tree.read_text()
        lib=self.lib.read_text()
        tests=self.tests.read_text()
        self.assertIn(TREE_MARKER,tree)
        self.assertIn("qp_poseidon_core::hash_to_bytes(&felts)",tree)
        self.assertIn("felts.extend(u64_to_felts(transfer_count))",tree)
        self.assertIn("amount_base_units as u64",tree)
        self.assertIn(LEDGER_MARKER,lib)
        self.assertIn("pallet_zk_tree::tree::dvn_native_v2_commitment_from_receipt",lib)
        self.assertIn("DvnV2EscrowCommitment::<T>::insert(id,commitment)",lib)
        self.assertIn("<AccountId32 as AsRef<[u8]>>::as_ref(&who)",tests)
        self.assertIn("DvnV2EscrowReceipt::<T>::insert(id,(recipient_bytes,count,amount_base_units));",lib)
        self.assertIn("TransactionOutcome::Rollback(Err(err))",lib)
        self.assertNotIn("pub fn devnira_v2_record_native_escrow_internal",lib)
        self.assertIn("dvn_v2_deposit_receipt_commitments_match_exact_poseidon_native_tree",tests)
        self.assertIn("dvn_v2_deposit_failed_debit_creates_no_poseidon_commitment",tests)
        with self.assertRaisesRegex(ValueError,"already installed"):
            patch(self.root)
    def test_missing_components_fail_closed_without_any_partial_write(self):
        before=self.lib.read_text()
        for filename,old,new in [
            (self.lib,"DEVNIRA_V2_NATIVE_ESCROW_BACKING_INTERNAL_NO_DISPATCH","DRIFT"),
            (self.tests,"DEVNIRA_V2_NATIVE_ESCROW_CUSTODY_NATIVE_FRAME_TESTS","DRIFT"),
            (self.tree,"pub fn hash_leaf_native_v2<T: Config>(","WRONG_TREE"),
        ]:
            original=filename.read_text()
            filename.write_text(original.replace(old,new))
            snapshot=(self.lib.read_text(),self.tests.read_text(),self.tree.read_text())
            with self.assertRaisesRegex(ValueError,"STOP"):
                patch(self.root)
            self.assertEqual(snapshot,(self.lib.read_text(),self.tests.read_text(),self.tree.read_text()))
            filename.write_text(original)
        self.assertEqual(before,self.lib.read_text())
if __name__=="__main__":
    unittest.main()
