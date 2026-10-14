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
