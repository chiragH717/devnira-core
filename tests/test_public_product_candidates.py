import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services.network_rpc import ChainRejected, GuardedRpc, NodeIdentity
from services.explorer_api import query
from pool.share_ledger import AccountingCandidate, VerifiedShareRecord

GENESIS = "0x" + "a1" * 32
HEAD = "0x" + "b2" * 32


def rpc_mock(method, params):
    if method == "chain_getBlockHash":
        return GENESIS if params == [0] else HEAD if params == [7] else None
    if method == "system_properties":
        return {"tokenDecimals": 8, "tokenSymbol": "DVN", "ss58Format": 190}
    if method == "system_chain":
        return "DEVNIRA Independent Development"
    if method == "chain_getFinalizedHead":
        return HEAD
    if method == "chain_getHeader":
        return {"number": "0x7"}
    if method == "chain_getBlock":
        return {"block": {"header": {"number": "0x7"}, "extrinsics": ["0x1234"]}}
    raise AssertionError("Unexpected RPC method")


class NetworkRpcTests(unittest.TestCase):
    def setUp(self):
        self.client = GuardedRpc(NodeIdentity("http://127.0.0.1:9944", GENESIS))

    def test_blocks_remote_hosts_credentials_invalid_genesis(self):
        for url in ("https://remote.example:9944", "http://example.com:9944",
                    "http://127.0.0.1:9944/a", "http://user:pass@localhost:9944"):
            with self.assertRaises(ChainRejected):
                NodeIdentity(url, GENESIS)
        with self.assertRaises(ChainRejected):
            NodeIdentity("http://localhost:9944", "0x" + "0" * 64)

    def test_must_verify_correct_chain_properties_and_genesis(self):
        with patch.object(self.client, "call", side_effect=rpc_mock):
            value = self.client.finalized_status()
            self.assertEqual(value["finalized_height"], 7)
            self.assertFalse(value["mainnet_ready"])
            self.assertEqual(self.client.block_at_height(7)["extrinsics_hex"], ["0x1234"])
            self.assertIsNone(self.client.block_at_height(9))
            self.assertEqual(query(self.client, "/api/block/7")[0], 200)
            self.assertEqual(query(self.client, "/api/block/9")[0], 404)
            self.assertEqual(query(self.client, "/api/anything")[0], 404)
            with self.assertRaises(ChainRejected):
                self.client.block_at_height(-1)

    def test_fails_closed_on_genesis_and_decimals_mismatch(self):
        def bad_genesis(method, params=None):
            if method == "chain_getBlockHash":
                return "0x" + "c3" * 32
            return rpc_mock(method, params)
        with patch.object(self.client, "call", side_effect=bad_genesis):
            with self.assertRaisesRegex(ChainRejected, "genesis"):
                self.client.finalized_status()
        def wrong_precision(method, params=None):
            if method == "system_properties":
                return {"tokenDecimals": 12, "tokenSymbol": "DVN", "ss58Format": 190}
            return rpc_mock(method, params)
        with patch.object(self.client, "call", side_effect=wrong_precision):
            with self.assertRaisesRegex(ChainRejected, "8-decimal"):
                self.client.finalized_status()

    def test_jsonrpc_reply_must_match_id_and_size(self):
        class Response:
            status = 200
            def __init__(self, data):
                self.data = data
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, count):
                return self.data[:count]
        with patch("services.network_rpc.urlopen",
                   return_value=Response(b'{"jsonrpc":"2.0","id":2,"result":null}')):
            with self.assertRaisesRegex(ChainRejected, "JSON-RPC"):
                self.client.call("system_chain")
        with patch("services.network_rpc.urlopen",
                   return_value=Response(b"x" * (1024 * 1024 + 1))):
            with self.assertRaisesRegex(ChainRejected, "1MiB"):
                self.client.call("system_chain")
        with self.assertRaises(ChainRejected):
            self.client.call("author_submitExtrinsic", ["0xdead"])


class OfflineShareLedgerTests(unittest.TestCase):
    def test_deterministic_integer_payout_and_replay_rejection(self):
        ledger = AccountingCandidate()
        a = VerifiedShareRecord("worker-A", "a" * 64, 2, "externally validated")
        b = VerifiedShareRecord("worker-B", "b" * 64, 1, "externally validated")
        ledger.record_from_external_verifier(a)
        ledger.record_from_external_verifier(b)
        self.assertEqual(ledger.preview_proportional_distribution(5),
                         {"worker-A": 3, "worker-B": 2})
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            ledger.record_from_external_verifier(a)
        ledger.seal()
        with self.assertRaisesRegex(ValueError, "sealed"):
            ledger.record_from_external_verifier(
                VerifiedShareRecord("worker-C", "c" * 64, 1, "external"))

    def test_cannot_mint_or_accept_invalid_shares(self):
        ledger = AccountingCandidate()
        with self.assertRaises(ValueError):
            ledger.preview_proportional_distribution(1)
        for share in (
            VerifiedShareRecord("../bad", "a" * 64, 1, "external"),
            VerifiedShareRecord("valid", "invalid", 1, "external"),
            VerifiedShareRecord("valid", "a" * 64, True, "external"),
            VerifiedShareRecord("valid", "a" * 64, 1, ""),
        ):
            with self.assertRaises(ValueError):
                ledger.record_from_external_verifier(share)
        ledger.record_from_external_verifier(
            VerifiedShareRecord("valid", "a" * 64, 1, "external"))
        with self.assertRaises(ValueError):
            ledger.preview_proportional_distribution(10_000_000_000_000_001)


class WebsiteTests(unittest.TestCase):
    def test_website_requires_honest_nonlive_disclosures(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / "website/index.html").read_text()
        for text in ("NOT mainnet", "90,000,000", "3M liquid",
                     "7M locked", "Android", "Explorer", "devnira.co"):
            self.assertIn(text, html)
        self.assertNotIn('href="/downloads/', html)
        self.assertTrue((root / "website/styles.css").exists())
        self.assertTrue((root / "website/app.js").exists())


if __name__ == "__main__":
    unittest.main()
