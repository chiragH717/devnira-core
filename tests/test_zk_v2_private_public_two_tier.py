"""Fail closed if production/dummy VK sneaks into REAL two-tier V2 prover/FRAME tests."""
import tempfile
import unittest
from pathlib import Path
from scripts.patch_zk_v2_private_public_fixed_vk import patch as patch_prover, MARKER as PM
from scripts.patch_zk_v2_private_public_frame_integration import patch as patch_frame, MARKER as FM

class V2PrivatePublicSourceTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.native=self.root/"wormhole/circuit/src/devnira_v2_amount_circuit.rs"
        self.frame=self.root/"pallets/wormhole/src/tests.rs"
        self.native.parent.mkdir(parents=True)
        self.frame.parent.mkdir(parents=True)
        self.native.write_text(
            "DEVNIRA_V2_AUTHENTICATED_22PI_FIXED_VK_RECURSION\n"
            "fn dvn_v2_recursive_authenticated_22pi(\n"
            "fn dvn_v2_recursive22_two_distinct_real_nullifiers_aggregate_and_replay_fails()\n"
            "    #[test]\n"
            "    fn dvn_v2_recursive22_rejects_same_abi_foreign_verifier_key() {\n")
        self.frame.write_text(
            "DEVNIRA_V2_ATOMIC_ESCROW_REAL_CRYPTO_ECONOMICS_TESTS\n"
            "DEVNIRA_V2_FRAME_CRYPTO_PROOF_BYTES_COMPAT_TEST_ONLY\n")

    def test_constrained_private_and_public_both_fixed_key_and_real_native(self):
        patch_prover(self.root)
        s=self.native.read_text()
        for invariant in (
            PM,
            "fn dvn_v2_private_single_leaf_fixed_vk(",
            "let (private, leaf_targets)=dvn_v2_private_single_leaf_fixed_vk(&inner)",
            "b.verify_proof::<C>(&p,&vk,&inner.common)",
            "b.constant_verifier_data::<C>(&private.verifier_only)",
            "b.verify_proof::<C>(&p,&fixed_private_vk,&private.common)",
            "b.assert_zero(all_nullifiers_equal)",
            "[0usize,3,16,17,18,19,20]",
            "b.connect(pi[22],exits)",
            "b.connect(pi[23],fee)",
            "b.range_check(v,54)",
            "dvn_v2_private_public_aggregator_real_two_level_same_history",
            "private-v2-24pi-proof.bin","private-v2-24pi-vk.bin",
            "public-v2-50pi-proof.bin","public-v2-50pi-vk.bin",
            "cross-private-batch nullifier replay accepted",
            "public aggregator accepted a foreign private verifier key",
        ):
            self.assertIn(invariant,s)
        with self.assertRaisesRegex(ValueError,"already applied"):
            patch_prover(self.root)

    def test_actual_frame_public_proof_settlement_storage_replay(self):
        patch_frame(self.root)
        s=self.frame.read_text()
        for invariant in (
            FM,"CommonCircuitData::from_bytes",
            "verifier.verify(decoded.clone())",
            "private-v2-24pi","public-v2-50pi",
            "devnira_v2_settle_verified_escrow_test_only",
            "Balances::total_issuance()",
            "Wormhole::used_nullifiers",
            "public aggregate first segment must contain genuine verified PRIVATE proof",
            "private-v2-24pi-other",
            "public aggregate second segment must contain genuine verified PRIVATE proof",
            "insufficient escrow must atomically roll back",
        ):
            self.assertIn(invariant,s)
        with self.assertRaisesRegex(ValueError,"already staged"):
            patch_frame(self.root)

    def test_missing_authenticated_native_proof_does_not_patch(self):
        self.native.write_text("UNTRUSTED PROOF")
        with self.assertRaisesRegex(ValueError,"prior authenticated fixed-VK"):
            patch_prover(self.root)

    def test_missing_real_frame_escrow_is_rejected(self):
        self.frame.write_text("UNTRUSTED FRAME")
        with self.assertRaisesRegex(ValueError,"proof-byte escrow"):
            patch_frame(self.root)

if __name__=="__main__":
    unittest.main()
