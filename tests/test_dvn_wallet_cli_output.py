import unittest
from scripts.check_dvn_cli_address import parse_public_wallet_output
from spec.ss58_company_account import encode_ss58_account

PUBLIC = encode_ss58_account(bytes(range(1, 33)))
DERIVATION = "Deriving HD path: m/44'/900190'/0'/0'/0'"

class DvnWalletOutputTests(unittest.TestCase):
    def test_public_account_from_isolated_wallet(self):
        text = f"{DERIVATION}\nAddress: {PUBLIC}\n"
        self.assertEqual(parse_public_wallet_output(text), PUBLIC)

    def test_quantus_network_and_old_hd_path_rejected(self):
        wrong = encode_ss58_account(bytes(range(1, 33)), prefix=189)
        for output in [
            f"{DERIVATION}\nAddress: {wrong}\n",
            f"Deriving HD path: m/44'/354'/0'/0'/0'\nAddress: {PUBLIC}\n",
            f"{DERIVATION}\nAddress: {PUBLIC}\nAddress: {PUBLIC}\n",
            f"{DERIVATION}\n",
            f"{DERIVATION}\nAddress: invalid_account\n",
        ]:
            with self.assertRaises(ValueError):
                parse_public_wallet_output(output)

    def test_never_accept_stdout_secret_material(self):
        text=f"{DERIVATION}\nAddress: {PUBLIC}\n"
        for word in ["Secret phrase: ", "Secret Key: ", "Seed Hex: "]:
            with self.assertRaisesRegex(ValueError, "secret material"):
                parse_public_wallet_output(text + word + "do-not-log\n")

if __name__=="__main__":
    unittest.main()
