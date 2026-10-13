import unittest
from wallet.network_identity import validate_local_rpc, validate_identity

class NetworkIdentityTests(unittest.TestCase):
    def test_local_rpc_only(self):
        self.assertEqual(validate_local_rpc("http://127.0.0.1:9944"), "http://127.0.0.1:9944")
        for url in ["https://127.0.0.1:9944", "http://evil.example:9944",
                    "http://localhost:9944@evil.example", "http://127.0.0.1:9944/private",
                    "http://localhost", "http://localhost:9944?token=secret"]:
            with self.assertRaises(ValueError):
                validate_local_rpc(url)

    def test_requires_pinned_genesis_and_runtime(self):
        genesis = "0x" + "ab" * 32
        validate_identity("DEVNIRA local", {"specName": "devnira-runtime"}, genesis, genesis)
        for chain, runtime, value, expected in [
            ("Quantus", {"specName": "devnira-runtime"}, genesis, genesis),
            ("DEVNIRA", {"specName": "quantus-runtime"}, genesis, genesis),
            ("DEVNIRA", {"specName": "devnira-runtime"}, genesis, "0x" + "cd" * 32),
            ("DEVNIRA", {"specName": "devnira-runtime"}, genesis, ""),
        ]:
            with self.assertRaises(ValueError):
                validate_identity(chain, runtime, value, expected)

if __name__ == "__main__":
    unittest.main()
