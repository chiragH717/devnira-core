import tempfile
import unittest
from pathlib import Path
from scripts.patch_zk_v2_22pi_leaf_candidate import patch,MARKER,ABI

class V2Canonical22PiTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.gadget=self.root/"wormhole/circuit/src/devnira_v2_amount_circuit.rs"
        self.gadget.parent.mkdir(parents=True)
        self.gadget.write_text("pub const DVN_NATIVE_MAX:u64=1;\n"+
            "pub fn constrain_native_dvn_authenticated_spend(x:u8){}\n"+
            "pub fn constrain_native_dvn_value_conservation(x:u8){}\n")
        self.abi=self.root/"wormhole/inputs/src/lib.rs"
        self.abi.parent.mkdir(parents=True)
        self.abi.write_text("\n".join(
            f"pub const {name}: usize = {value};" for name,value in ABI.items()))

    def test_pinned_22_felt_zk_proof_and_negative_witnesses_inserted(self):
        old=self.gadget.read_bytes()
        patch(self.root)
        src=self.gadget.read_text()
        self.assertTrue(src.startswith(old.decode()))
        for keyword in (MARKER,"b.register_public_inputs(&pi)",
                        "assert_eq!(data.common.num_public_inputs,LEN)",
                        "dvn_v2_22pi_exact_native_layout_proof_and_tamper_check",
                        "dvn_v2_22pi_bad_commitments_and_amounts_do_not_prove"):
            self.assertIn(keyword,src)
        with self.assertRaisesRegex(ValueError,"already staged"):
            patch(self.root)

    def test_upstream_wire_layout_drift_is_fatal_and_atomic(self):
        old=self.gadget.read_bytes()
        self.abi.write_text(self.abi.read_text().replace(
            "pub const INPUT_AMOUNT_INDEX: usize = 21;",
            "pub const INPUT_AMOUNT_INDEX: usize = 20;"))
        with self.assertRaisesRegex(ValueError,"canonical 22 PI leaf drift"):
            patch(self.root)
        self.assertEqual(self.gadget.read_bytes(),old)

    def test_missing_authenticated_native_value_gadget_fails(self):
        self.gadget.write_text("pub const DVN_NATIVE_MAX:u64=1;")
        with self.assertRaisesRegex(ValueError,"Missing native amount"):
            patch(self.root)

if __name__=="__main__":
    unittest.main()
