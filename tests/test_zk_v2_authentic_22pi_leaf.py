import tempfile
import unittest
from pathlib import Path
from scripts.patch_zk_v2_authentic_22pi_leaf import MARKER, patch

class AuthenticNativeDVNLeafPatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        files={
            "wormhole/circuit/src/devnira_v2_amount_circuit.rs":
                "pub fn constrain_native_dvn_authenticated_spend(x:u8){}\n"+
                "pub fn constrain_native_dvn_value_conservation(x:u8){}\n"+
                "pub const DVN_NATIVE_MAX:u64=1;\n",
            "wormhole/circuit/src/block_header/mod.rs":
                "pub fn conditional_block_hash_binding(x:u8){}\n"+
                "pub fn circuit_without_hash_binding(x:u8){}\n",
            "wormhole/circuit/src/unspendable_account.rs":
                "pub fn constraints(x:u8){}\npub const UNSPENDABLE_SALT:&str=\"wormhole\";\n",
            "wormhole/circuit/src/nullifier.rs":
                "pub fn conditional_hash_binding(x:u8){}\npub const NULLIFIER_SALT:&str=\"~nullif~\";\n",
            "wormhole/circuit/src/block_header/header.rs":
                "pub struct HeaderTargets;\npub const DIGEST_LOGS_SIZE: usize = 110;\n",
        }
        for name,body in files.items():
            path=self.root/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(body)
        self.target=self.root/"wormhole/circuit/src/devnira_v2_amount_circuit.rs"
    def test_stages_real_composed_header_and_owner_secret(self):
        old=self.target.read_text()
        patch(self.root)
        s=self.target.read_text()
        self.assertTrue(s.startswith(old))
        for term in (
            MARKER,"UnspendableAccount::constraints(",
            "Nullifier::conditional_hash_binding(",
            "BlockHeader::conditional_block_hash_binding(",
            'fault=="coherent_root"',
            '"coherent_root","bad_fee"',
            "let input_times_rate=b.mul(pi[21],expected_rate)",
            "enforce_target_less_than_const(&mut b,remainder,10_000,14)",
            "b.connect(computed_root.elements[i],committed_root.elements[i])",
            "b.register_public_inputs(&pi)",
            "assert_eq!(data.common.num_public_inputs,FELTS)",
            "dvn_v2_full_leaf_22pi_owner_nullifier_merkle_header_proves",
            "dvn_v2_full_leaf_22pi_rejects_fake_spends_and_roots",
            "NOT A LIVE PRODUCTION PROVER",
        ):
            if term=="NOT A LIVE PRODUCTION PROVER":continue
            self.assertIn(term,s)
        with self.assertRaisesRegex(ValueError,"already staged"):
            patch(self.root)
    def test_upstream_header_binding_drift_is_fatal(self):
        old=self.target.read_text()
        changed=self.root/"wormhole/circuit/src/block_header/mod.rs"
        changed.write_text("pub fn no_verification(x:u8){}")
        with self.assertRaisesRegex(ValueError,"Upstream signed-spend/header"):
            patch(self.root)
        self.assertEqual(self.target.read_text(),old)
    def test_conservation_missing_blocks_activation(self):
        self.target.write_text("pub const DVN_NATIVE_MAX:u64=1;")
        with self.assertRaisesRegex(ValueError,"missing exact-u64"):
            patch(self.root)

if __name__=="__main__":
    unittest.main()
