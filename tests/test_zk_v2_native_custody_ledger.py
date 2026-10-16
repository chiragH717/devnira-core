"""Fail-closed source-injection checks; GitHub CI compiles actual FRAME tests."""
import tempfile
import unittest
from pathlib import Path
from scripts.patch_zk_v2_native_custody_ledger import patch,MARKER

class NativeV2CustodyTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        src=self.root/"pallets/wormhole/src"
        src.mkdir(parents=True)
        self.lib=src/"lib.rs"
        self.tests=src/"tests.rs"
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
        self.tests.write_text("// retained FRAME tests\n")
    def test_deposit_custody_accounting_and_no_dispatch(self):
        patch(self.root)
        data=self.lib.read_text()
        tests=self.tests.read_text()
        for token in [MARKER,"DvnV2EscrowTotal<T:Config>",
                     "DvnV2EscrowRecipientCount<T:Config>",
                     "PalletId(*b\"dvn/v2es\")",
                     "with_transaction(||","Preservation::Preserve",
                     "TransactionOutcome::Rollback(Err(err))",
                     "DvnV2EscrowTotal::<T>::put(total)",
                     "dest==Self::devnira_v2_custody_escrow_account()"]:
            self.assertIn(token,data)
        self.assertNotIn("pub fn devnira_v2_record_native_escrow_internal",data)
        self.assertIn("DEVNIRA_V2_NATIVE_ESCROW_CUSTODY_NATIVE_FRAME_TESTS",tests)
        self.assertIn("dvn_v2_deposit_exact_base_unit_native_accounting_no_mint",tests)
        self.assertIn("dvn_v2_deposit_bad_alias_zero_overflow_vault_and_failed_debit_reject",tests)
        self.assertIn("Balances::total_issuance()",tests)
        self.assertIn("use frame_support::traits::fungible::Inspect;",tests)
        self.assertIn("dvn_v2_deposit_independent_recipients_and_exact_receipt_order",tests)
        self.assertIn("dvn_v2_deposit_underbacked_vault_and_reused_receipt_fail_atomically",tests)
        self.assertIn("!DvnV2EscrowReceipt::<T>::contains_key(id)",data)
        with self.assertRaisesRegex(ValueError,"already installed"):
            patch(self.root)
    def test_pinned_source_drift_aborts_without_partial_write(self):
        base=self.lib.read_text()
        for token in ["pub fn verify_private_batch(","Self::record_transfer(T::AssetId::default(), &from, &to, amount);"]:
            self.lib.write_text(base.replace(token,"FORBIDDEN_DRIFT"))
            before=self.lib.read_text()
            with self.assertRaisesRegex(ValueError,"STOP"):
                patch(self.root)
            self.assertEqual(before,self.lib.read_text())
if __name__=="__main__":
    unittest.main()
