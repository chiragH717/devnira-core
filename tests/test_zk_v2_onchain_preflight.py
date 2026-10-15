import tempfile
import unittest
from pathlib import Path
from scripts.patch_zk_v2_onchain_preflight import patch,MARKER,TEST_MARKER,ABI

class RealFrameV2AbiTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.chain=Path(self.tmp.name)/"chain"
        lib=self.chain/"pallets/wormhole/src/lib.rs"
        lib.parent.mkdir(parents=True)
        lib.write_text(
            "pub(super) type UsedNullifiers<T: Config> = X;\n"
            "pub(crate) fn validate_exit_bundle_common(x:u8) {}\n"
            "pub fn verify_private_batch(x:u8) {}\n"
            "\t\tfn segment_is_inert(segment: &ExitSegment) -> bool { true }\n")
        (lib.parent/"tests.rs").write_text("// upstream fixture\n")
        self.lib=lib
        self.circuits=Path(self.tmp.name)/"circuits"
        file=self.circuits/"wormhole/inputs/src/lib.rs"
        file.parent.mkdir(parents=True)
        file.write_text(
            "pub const PUBLIC_INPUTS_FELTS_LEN: usize = 22;\n"+
            "".join(f"pub const {name}: usize = {value};\n" for name,value in ABI.items()))
        self.abi=file

    def test_onchain_helper_and_real_storage_tests_staged(self):
        patch(self.chain,self.circuits)
        src=self.lib.read_text()
        tests=(self.lib.parent/"tests.rs").read_text()
        for requirement in (MARKER, "pis.len() == 22",
                           "UsedNullifiers::<T>::contains_key(nullifier)",
                           "frame_system::Pallet::<T>::block_hash",
                           "historical_number < frame_system::Pallet::<T>::block_number()",
                           "input > 0 && input <= MAX_NATIVE",
                           "total.checked_add(expected_fee) == Some(input)",
                           "known.as_ref() == claimed.as_ref()"):
            self.assertIn(requirement,src)
        for test in ("dvn_v2_abi_valid_real_frame_storage_is_read_only",
                     "dvn_v2_abi_replay_and_wrong_history_are_rejected",
                     "dvn_v2_abi_bad_15pi_amount_network_and_nullifiers_rejected",
                     "dvn_v2_abi_exact_4bps_fee_and_single_base_unit_rounding",
                     "dvn_v2_abi_future_block_hash_cannot_authorize_a_spend"):
            self.assertIn(test,tests)
        self.assertIn(TEST_MARKER,tests)
        with self.assertRaisesRegex(ValueError,"already staged"):
            patch(self.chain,self.circuits)

    def test_wrong_abi_fails_without_changes(self):
        old=self.lib.read_bytes()
        self.abi.write_text(self.abi.read_text().replace(
            "pub const BLOCK_HASH_START_INDEX: usize = 16;",
            "pub const BLOCK_HASH_START_INDEX: usize = 15;"))
        with self.assertRaisesRegex(ValueError,"ABI drift"):
            patch(self.chain,self.circuits)
        self.assertEqual(self.lib.read_bytes(),old)

    def test_missing_active_replay_storage_fails_closed(self):
        self.lib.write_text("pub fn verify_private_batch(x:u8) {}")
        with self.assertRaisesRegex(ValueError,"Upstream consensus source changed"):
            patch(self.chain,self.circuits)

if __name__=="__main__":
    unittest.main()
