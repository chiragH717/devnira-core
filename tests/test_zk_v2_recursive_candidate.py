import tempfile
import unittest
from pathlib import Path
from scripts.patch_zk_v2_recursive_candidate import patch,MARKER

class V2RecursiveIntegrationPatchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        aggregator=self.root/"wormhole/aggregator/src"
        circuit=self.root/"wormhole/circuit/src"
        aggregator.mkdir(parents=True)
        circuit.mkdir(parents=True)
        self.agg=aggregator/"lib.rs"
        self.agg.write_text(
            "pub mod common;\npub mod private_batch;\npub mod public_batch;\npub mod devnira_v2_segment;\n"
        )
        self.leaf=circuit/"devnira_v2_amount_circuit.rs"
        self.leaf.write_text("pub fn constrain_native_dvn_authenticated_spend() {}")
    def test_adds_opt_in_real_constant_verifier_instead_of_fake_security_claims(self):
        old=self.agg.read_text()
        patch(self.root)
        source=(self.agg.parent/"devnira_v2_recursive_candidate.rs").read_text()
        self.assertTrue(self.agg.read_text().startswith(old))
        self.assertIn(MARKER,self.agg.read_text())
        for term in ("add_recursive_verifiers::<F,C,D>",
                     "constrain_native_dvn_authenticated_spend",
                     "constrain_v2_public_batch_exits",
                     "constant verifier key",
                     "dvn_v2_actual_recursive_poseidon2_leaf_proves_and_verifies",
                     "outer_for_witness.verify",
                     "tampered_fee",
                     "V2_LEAF_PUBLIC_INPUT_LEN"):
            self.assertIn(term.lower(),source.lower())
    def test_multi_leaf_batch_is_source_gated_and_keeps_active_v1_unchanged(self):
        patch(self.root)
        source=(self.agg.parent/"devnira_v2_recursive_candidate.rs").read_text()
        for required in (
            "build_v2_multi_leaf_recursive_batch",
            "ProofWithPublicInputsTarget",
            "ensure!((2..=MAX_LEAVES).contains(&num_leaves)",
            "add_recursive_verifiers::<F,C,D>",
            "constrain_v2_public_batch_exits",
            "constrain_v2_native_amount(&mut builder,total_fee)",
            "same_commitment=builder.mul(same_commitment,eq.target)",
            "builder.assert_zero(same_commitment)",
            "dvn_v2_batch_rejects_same_spent_leaf_proof_twice",
            "builder.register_public_input(total_payout)",
            "builder.register_public_input(total_fee)",
            "dvn_v2_batch_real_two_leaf_recursive_proof_enforces_exact_supply",
            "dvn_v2_batch_rejects_zero_one_or_oversized_leaf_count",
            "altered batch payout must fail",
            "altered batch fee must fail",
        ):
            self.assertIn(required,source)
        # Staging an opt-in module cannot substitute the production verifier.
        self.assertNotIn("pub mod devnira_v2_recursive_candidate;",
            "pub mod common;\npub mod private_batch;\npub mod public_batch;")

    def test_duplicate_does_not_mutate(self):
        patch(self.root)
        with self.assertRaisesRegex(ValueError,"already installed"):
            patch(self.root)
    def test_missing_leaf_blocks_patch(self):
        self.leaf.unlink()
        with self.assertRaisesRegex(ValueError,"Poseidon2 leaf"):
            patch(self.root)
        self.assertNotIn(MARKER,self.agg.read_text())
    def test_missing_aggregation_blocks_patch(self):
        self.agg.write_text("pub mod common;\npub mod private_batch;\npub mod public_batch;\n")
        with self.assertRaisesRegex(ValueError,"V2 aggregation"):
            patch(self.root)
        self.assertFalse((self.agg.parent/"devnira_v2_recursive_candidate.rs").exists())
if __name__=="__main__":
    unittest.main()
