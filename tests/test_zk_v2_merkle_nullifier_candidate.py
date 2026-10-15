import tempfile
import unittest
from pathlib import Path
from scripts.patch_zk_v2_merkle_nullifier_candidate import patch,MARKER

class NativeDvnMerkleNullifierCandidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.file=Path(self.tmp.name)/"wormhole/circuit/src/devnira_v2_amount_circuit.rs"
        self.file.parent.mkdir(parents=True)
        self.file.write_text(
            "pub const DVN_NATIVE_MAX: u64=10_000_000_000_000_000;\n"
            "pub fn constrain_native_dvn_authenticated_spend() {}\n"
            "pub fn constrain_native_dvn_value_conservation() {}\n")
        self.root=Path(self.tmp.name)

    def test_adds_real_verifiable_zk_merkle_and_nullifier_constraints(self):
        patch(self.root)
        text=self.file.read_text()
        for required in (
            MARKER,
            "constrain_native_dvn_authenticated_spend(",
            "constrain_native_dvn_value_conservation",
            "b.poseidon2_hash_no_pad(preimage)",
            "b.connect(*got,*expected)",
            "b.register_public_inputs(&root.elements)",
            "b.register_public_inputs(&chain_hash.elements)",
            "b.register_public_inputs(&nullifier.elements)",
            "b.range_check(position,2)",
            "b.assert_zero(zero_tag)",
            "b.assert_zero(zero_input.target)",
            "dvn_v2_merkle_real_native_root_and_nullifier_proof",
            "dvn_v2_merkle_rejects_forged_root_sibling_and_nullifier",
            "dvn_v2_merkle_rejects_foreign_network_zero_and_reused_nullifier",
            "assert_eq!(data.common.num_public_inputs,15)",
        ):
            self.assertIn(required,text)
        self.assertIn("NOT ACTIVE",text)

    def test_existing_source_remains_at_start(self):
        initial=self.file.read_bytes()
        patch(self.root)
        self.assertTrue(self.file.read_bytes().startswith(initial))

    def test_reapplication_and_missing_conservation_fails_closed(self):
        patch(self.root)
        with self.assertRaisesRegex(ValueError,"already installed"):
            patch(self.root)
        self.file.write_text("pub fn constrain_native_dvn_authenticated_spend() {}")
        with self.assertRaisesRegex(ValueError,"conservation"):
            patch(self.root)
        self.assertNotIn(MARKER,self.file.read_text())

if __name__ == "__main__":
    unittest.main()
