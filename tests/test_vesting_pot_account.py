import unittest
from spec.ss58_company_account import encode_ss58_account, decode_ss58_account
from spec.vesting_pot import (
    FRAME_PALLET_ACCOUNT_PREFIX, VESTING_PALLET_ID,
    vesting_pot_account_id, vesting_pot_ss58, verify_vesting_pot_address,
)

class NativeVestingPotAccountTests(unittest.TestCase):
    def test_matches_frame_accountid32_pallet_id_derivation(self):
        account=vesting_pot_account_id()
        self.assertEqual(FRAME_PALLET_ACCOUNT_PREFIX,b"modl")
        self.assertEqual(VESTING_PALLET_ID,b"qvesting")
        self.assertEqual(account,b"modlqvesting"+bytes(20))
        self.assertEqual(len(account),32)
        self.assertEqual(decode_ss58_account(vesting_pot_ss58(),190),account)

    def test_pot_account_cannot_be_retargeted_in_manifest(self):
        real=vesting_pot_ss58()
        self.assertEqual(verify_vesting_pot_address(real),real)
        for fake in [
            encode_ss58_account(bytes([44]*32)),
            encode_ss58_account(vesting_pot_account_id(),189),
            "invented-account",
        ]:
            with self.assertRaises(ValueError):
                verify_vesting_pot_address(fake)

if __name__=="__main__":
    unittest.main()
