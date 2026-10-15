"""Fail-closed checks for proof-before-payout FRAME escrow source patch."""
import tempfile
import unittest
from pathlib import Path
from scripts.patch_zk_v2_atomic_escrow_test_only import patch, MARKER, TEST_MARKER

class V2AtomicEscrowSourceTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        folder=self.root/"pallets/wormhole/src"
        folder.mkdir(parents=True)
        self.lib=folder/"lib.rs"
        self.tests=folder/"tests.rs"
        self.lib.write_text(
            "DEVNIRA_V2_22_PI_PREFLIGHT_NO_SETTLEMENT\n"
            "DEVNIRA V2 FRAME BATCH GUARD DISTINCT NULLIFIERS NO SETTLEMENT\n"
            "\t\tfn segment_is_inert(segment: &ExitSegment) -> bool {\n}\n")
        self.tests.write_text(
            "DEVNIRA_V2_FRAME_CRYPTO_PROOF_BYTES_COMPAT_TEST_ONLY\n")

    def test_authenticated_exact_accounting_and_atomic_rollback_contract(self):
        patch(self.root)
        rust=self.lib.read_text()
        tests=self.tests.read_text()
        for guard in (
            MARKER, "#[cfg(test)]",
            "verifier.verify(proof.clone())", "NonCanonicalProofEncoding",
            "ProofWithPublicInputs::<F, C, D>::from_bytes",
            "pis[22*leaves] as u128 == summed_outputs",
            "pis[22*leaves+1] as u128 == summed_fees",
            "Self::devnira_v2_batch_chain_preflight(&batch)",
            "with_transaction(||",
            "TransactionOutcome::Commit(Ok(()))",
            "TransactionOutcome::Rollback(Err(err))",
            "UsedNullifiers::<T>::insert(spent, true)",
            "<T::Currency as Mutate<_>>::transfer(",
            "Preservation::Preserve",
        ):
            self.assertIn(guard,rust)
        for claim in (
            TEST_MARKER,"dvn_v2_crypto_real_escrow_one_leaf_pays_exact_amount_fee",
            "dvn_v2_crypto_real_escrow_two_leaf_atomic_exact_fee_and_replay",
            "dvn_v2_crypto_escrow_insufficient_funds_rolls_back_partial_payout",
            "dvn_v2_crypto_escrow_tamper_wrong_history_and_trailing_bytes",
            "Balances::total_issuance()",
        ):
            self.assertIn(claim,tests)
        with self.assertRaisesRegex(ValueError,"already staged"):
            patch(self.root)

    def test_cannot_install_without_crypto_verified_frame_bridge(self):
        self.tests.write_text("UNTRUSTED PROOF PIS")
        with self.assertRaisesRegex(ValueError,"proof-byte verifier"):
            patch(self.root)

    def test_cannot_install_without_replay_storage_gate(self):
        self.lib.write_text(
            "DEVNIRA_V2_22_PI_PREFLIGHT_NO_SETTLEMENT\n"
            "\t\tfn segment_is_inert(segment: &ExitSegment) -> bool {")
        with self.assertRaisesRegex(ValueError,"checked FRAME state gate"):
            patch(self.root)

if __name__=="__main__":unittest.main()
