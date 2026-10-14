"""Windows offline company wallet provisioning has no private-key exposure."""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from spec.ss58_company_account import encode_ss58_account
from wallet.company_wallet_prepare import (
    UnsafeWalletExecutable, create_offline_keygen_command,
    create_public_ownership_challenge, verified_native_wallet_binary,
    verify_offline_company_certificate,
)

ADDR=encode_ss58_account(bytes(range(1,33)))

class CompanyWindowsWalletTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.binary=Path(self.temp.name)/"audited'dvn-wallet-cli.exe"
        self.binary.write_bytes(b"FAKE BINARY TEST; NEVER A REAL COMPANY WALLET")
        self.pin=hashlib.sha256(self.binary.read_bytes()).hexdigest()

    def test_offline_keygen_command_rechecks_hash_in_powershell(self):
        command=create_offline_keygen_command(self.binary,self.pin)
        self.assertIn("Get-FileHash",command)
        self.assertIn(self.pin,command)
        self.assertIn("key devnira --scheme standard --wallet-index 0",command)
        self.assertIn("audited''dvn-wallet-cli.exe",command)
        self.assertNotIn("seed",command.lower())
        self.assertNotIn("mnemonic",command.lower())
        self.assertEqual(verified_native_wallet_binary(self.binary,self.pin),self.binary.resolve())

    def test_rejects_unverified_changed_executable_and_wrong_extension(self):
        for pin in ("","x"*64,self.pin.upper(),"0"*64):
            with self.assertRaises(UnsafeWalletExecutable):
                create_offline_keygen_command(self.binary,pin)
        self.binary.write_bytes(b"SWAPPED SINCE HASH")
        with self.assertRaisesRegex(UnsafeWalletExecutable,"SHA256"):
            create_offline_keygen_command(self.binary,self.pin)
        self.binary.rename(self.binary.with_suffix(".bat"))
        with self.assertRaises(UnsafeWalletExecutable):
            create_offline_keygen_command(self.binary.with_suffix(".bat"),
                                           hashlib.sha256(b"SWAPPED SINCE HASH").hexdigest())

    def test_rejects_symlink_and_invalid_wallet_index(self):
        with self.assertRaisesRegex(UnsafeWalletExecutable,"index"):
            create_offline_keygen_command(self.binary,self.pin,wallet_index=-1)
        with self.assertRaises(UnsafeWalletExecutable):
            create_offline_keygen_command(self.binary,self.pin,wallet_index=True)
        link=Path(self.temp.name)/"linked.exe"
        try:
            link.symlink_to(self.binary)
        except (OSError,NotImplementedError):
            return
        with self.assertRaisesRegex(UnsafeWalletExecutable,"Symlink"):
            create_offline_keygen_command(link,self.pin)

    def test_public_challenge_never_requires_live_rpc(self):
        challenge=create_public_ownership_challenge(ADDR)
        self.assertEqual(challenge["company_address"],ADDR)
        self.assertIn("DEVNIRA-COMPANY-GENESIS-OWNERSHIP-V1",challenge["message"])
        self.assertEqual(len(challenge["nonce"]),64)
        for wrong in ("", "not-ss58", encode_ss58_account(bytes(range(1,33)),prefix=189)):
            with self.assertRaises(ValueError):
                create_public_ownership_challenge(wrong)

    @patch("wallet.company_wallet_prepare.verify_company_certificate")
    def test_offline_signature_verification_never_imports_secrets(self, fake):
        fake.return_value={"company_address":ADDR,"ownership_signature_verified":True}
        signed={"company_address":ADDR,"public_key_hex":"0x0123","signature_hex":"0xbeef"}
        result=verify_offline_company_certificate(signed,self.binary,self.pin)
        self.assertEqual(result["company_address"],ADDR)
        fake.assert_called_once_with(signed,self.binary.resolve(),self.pin)
        with self.assertRaises(UnsafeWalletExecutable):
            verify_offline_company_certificate(signed,self.binary,"0"*64)
        self.assertEqual(fake.call_count,1)

if __name__=="__main__":
    unittest.main()
