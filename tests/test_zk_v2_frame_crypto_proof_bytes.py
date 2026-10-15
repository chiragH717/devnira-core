"""Verify no unsupported proof is silently substituted in the FRAME cryptographic bridge."""
import tempfile
import unittest
from pathlib import Path
from scripts.patch_zk_v2_frame_crypto_proof_bytes import patch, MARKER
from scripts.patch_zk_v2_authenticated_recursive_22pi import RUST_TESTS

class FrameCryptoProofCompatibilitySourceTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.lib=self.root/"pallets/wormhole/src/lib.rs"
        self.test=self.root/"pallets/wormhole/src/tests.rs"
        self.lib.parent.mkdir(parents=True)
        self.lib.write_text("DEVNIRA_V2_22_PI_PREFLIGHT_NO_SETTLEMENT\n"
            "DEVNIRA V2 FRAME BATCH GUARD DISTINCT NULLIFIERS NO SETTLEMENT")
        self.test.write_text("DEVNIRA_V2_REAL_PROVEN_22PI_FRAME_ABI_READ_ONLY_BRIDGE")

    def test_real_serialized_proof_requires_actual_frame_verifier(self):
        patch(self.root)
        s=self.test.read_text()
        for phrase in (MARKER, "VerifierOnlyCircuitData::from_bytes",
            "CommonCircuitData::from_bytes", "WormholeVerifier {",
            "ProofWithPublicInputs::<F,C,D>::from_bytes",
            "verifier.verify(proof.clone())",
            "assert_eq!(proof.to_bytes(),proof_bytes",
            "dvn_v2_realproof_frame_verifies_actual_24pi_recursive_bytes_then_storage",
            "dvn_v2_realproof_frame_verifies_both_full_depth_spends_one_history",
            "devnira_v2_batch_chain_preflight",
            "UsedNullifiers::<Test>::insert",
            "FRAME cryptographic recursive verification FAILED"):
            self.assertIn(phrase,s)
        with self.assertRaisesRegex(ValueError,"already installed"):
            patch(self.root)

    def test_absent_verified_batch_guard_fails_closed(self):
        self.lib.write_text("DEVNIRA_V2_22_PI_PREFLIGHT_NO_SETTLEMENT")
        before=self.test.read_bytes()
        with self.assertRaisesRegex(ValueError,"state guards"):
            patch(self.root)
        self.assertEqual(before,self.test.read_bytes())

    def test_incomplete_historical_bridge_fails_closed(self):
        self.test.write_text("missing")
        before=self.test.read_bytes()
        with self.assertRaisesRegex(ValueError,"history bridge"):
            patch(self.root)
        self.assertEqual(before,self.test.read_bytes())

    def test_recursive_layout_forbids_cross_history_batching(self):
        self.assertIn("b.connect(proofs[0].public_inputs[slot]",RUST_TESTS)
        self.assertIn("[0usize,3,16,17,18,19,20]",RUST_TESTS)
        self.assertIn("authentic",RUST_TESTS.lower())

if __name__=="__main__":
    unittest.main()
