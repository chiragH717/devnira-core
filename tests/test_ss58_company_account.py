import unittest

from spec.ss58_company_account import (
    DEVNIRA_SS58_PREFIX,
    InvalidCompanyAddress,
    decode_ss58_account,
    encode_ss58_account,
    verified_company_public_address,
)

# Public test vectors only — no signer, secret key or custody is created here.
ALICE_SUBSTRATE_TEST_VECTOR = "5GrwvaEF5zXb26Fz9rcQpDWSQMgULoe2S4vgtRWqbTCzbt7"
ALICE_SUBSTRATE_ACCOUNT = bytes.fromhex(
    "d43593c715fdd31c61141abd04a99fd6822c8558854ccde39a5684e7a56da27d"
)

class CompanySs58Tests(unittest.TestCase):
    def test_independent_standard_ss58_test_vector(self):
        # The public Substrate prefix-42 vector confirms standard SS58 checksum
        # interoperability. It is NEVER accepted as a DEVNIRA company account.
        self.assertEqual(
            decode_ss58_account(ALICE_SUBSTRATE_TEST_VECTOR, prefix=42),
            ALICE_SUBSTRATE_ACCOUNT,
        )
        self.assertEqual(
            encode_ss58_account(ALICE_SUBSTRATE_ACCOUNT, prefix=42),
            ALICE_SUBSTRATE_TEST_VECTOR,
        )
        with self.assertRaises(InvalidCompanyAddress):
            verified_company_public_address(ALICE_SUBSTRATE_TEST_VECTOR)

    def test_devnira_two_byte_ss58_network_prefix_190(self):
        for account in (bytes(range(1, 33)), bytes([255] * 32), ALICE_SUBSTRATE_ACCOUNT):
            address = encode_ss58_account(account)
            self.assertEqual(decode_ss58_account(address), account)
            self.assertEqual(verified_company_public_address(address), address)
            self.assertEqual(DEVNIRA_SS58_PREFIX, 190)
            self.assertNotEqual(address, encode_ss58_account(account, prefix=189))
            with self.assertRaises(InvalidCompanyAddress):
                decode_ss58_account(encode_ss58_account(account, prefix=189))

    def test_checksum_character_and_account_length_fail_closed(self):
        address = encode_ss58_account(bytes(range(1, 33)))
        replacement = "1" if address[-1] != "1" else "2"
        for invalid in (address[:-1] + replacement, "", address[:-1], " " + address,
                        "0" + address, address + "1", "test-company-address"):
            with self.assertRaises(InvalidCompanyAddress, msg=invalid):
                decode_ss58_account(invalid)

    def test_reject_zero_and_non_account_ids(self):
        for bad in (b"\0" * 32, b"\x01" * 31, b"\x01" * 33, b""):
            with self.assertRaises(InvalidCompanyAddress):
                encode_ss58_account(bad)
        for prefix in (-1, 16384, 190.0):
            with self.assertRaises(InvalidCompanyAddress):
                encode_ss58_account(bytes(range(1, 33)), prefix)

    def test_decoding_does_not_imply_key_ownership(self):
        # A syntactically valid synthetic public account does not prove custody
        # or the ability to sign a Dilithium transaction on an independent chain.
        account = bytes(range(1, 33))
        self.assertEqual(decode_ss58_account(encode_ss58_account(account)), account)

if __name__ == "__main__":
    unittest.main()
