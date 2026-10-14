"""Fail-closed localhost RPC client for an independent eight-decimal DVN chain.

Do not configure a Quantus dev or mainnet endpoint. This module never signs,
mines, indexes, or declares the DEVNIRA chain ready for mainnet.
"""
import json
import re
from dataclasses import dataclass
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

_HASH = re.compile(r"0x[0-9a-fA-F]{64}\Z")
_ALLOWED = frozenset({
    "chain_getBlockHash", "chain_getFinalizedHead", "chain_getHeader",
    "chain_getBlock", "system_chain", "system_properties",
})
MAX_REPLY_BYTES = 1024 * 1024


class ChainRejected(ValueError):
    """Refuse unverified or incompatible network data."""


def valid_hash(value):
    return isinstance(value, str) and _HASH.fullmatch(value) is not None


@dataclass(frozen=True)
class NodeIdentity:
    rpc_url: str
    genesis_hash: str

    def __post_init__(self):
        parts = urlsplit(self.rpc_url)
        if (parts.scheme != "http" or parts.hostname not in ("127.0.0.1", "localhost")
                or parts.username is not None or parts.password is not None
                or parts.path not in ("", "/") or parts.query or parts.fragment):
            raise ChainRejected("Only a local HTTP node RPC is accepted; deploy a reverse proxy separately")
        if parts.port is None or not 1 <= parts.port <= 65535:
            raise ChainRejected("Explicit local RPC port required")
        if not valid_hash(self.genesis_hash) or self.genesis_hash == "0x" + "0" * 64:
            raise ChainRejected("Set a nonzero, independently verified 32-byte genesis hash")


class GuardedRpc:
    def __init__(self, identity: NodeIdentity, timeout: float = 4.0):
        if timeout <= 0 or timeout > 30:
            raise ValueError("RPC timeout outside safe bounds")
        self.identity = identity
        self.timeout = timeout

    def call(self, method, params=None):
        if method not in _ALLOWED:
            raise ChainRejected("RPC method is not permitted")
        body = json.dumps({"jsonrpc": "2.0", "method": method,
                           "params": [] if params is None else params, "id": 1}).encode("utf-8")
        request = Request(self.identity.rpc_url, data=body, headers={
            "Content-Type": "application/json", "Accept": "application/json",
        }, method="POST")
        with urlopen(request, timeout=self.timeout) as reply:
            if reply.status != 200:
                raise ChainRejected("Node RPC rejected the request")
            data = reply.read(MAX_REPLY_BYTES + 1)
        if len(data) > MAX_REPLY_BYTES:
            raise ChainRejected("RPC result exceeds 1MiB cap")
        try:
            decoded = json.loads(data)
        except (ValueError, UnicodeDecodeError) as exc:
            raise ChainRejected("RPC response is not JSON") from exc
        if (not isinstance(decoded, dict) or decoded.get("jsonrpc") != "2.0"
                or decoded.get("id") != 1 or decoded.get("error") is not None
                or "result" not in decoded):
            raise ChainRejected("Malformed or unsuccessful JSON-RPC reply")
        return decoded["result"]

    def verify_identity(self):
        genesis = self.call("chain_getBlockHash", [0])
        props = self.call("system_properties")
        chain = self.call("system_chain")
        if not valid_hash(genesis) or genesis.lower() != self.identity.genesis_hash.lower():
            raise ChainRejected("Connected node genesis differs from pinned DEVNIRA genesis")
        if not isinstance(props, dict):
            raise ChainRejected("Node does not expose valid chain properties")
        def one(key):
            value = props.get(key)
            if isinstance(value, list):
                if len(value) != 1:
                    raise ChainRejected("Ambiguous chain property: " + key)
                value = value[0]
            return value
        if (type(one("tokenDecimals")) is not int or one("tokenDecimals") != 8
                or one("tokenSymbol") != "DVN"
                or type(one("ss58Format")) is not int or one("ss58Format") != 190):
            raise ChainRejected("RPC is not exact 8-decimal DVN (symbol/SS58 mismatch)")
        if not isinstance(chain, str) or "devnira" not in chain.lower() or "quantus" in chain.lower():
            raise ChainRejected("RPC chain name is foreign or ambiguous")
        return {"genesis_hash": genesis, "chain": chain,
                "token_symbol": "DVN", "token_decimals": 8, "ss58_format": 190}

    def finalized_status(self):
        identity = self.verify_identity()
        head = self.call("chain_getFinalizedHead")
        if not valid_hash(head):
            raise ChainRejected("Invalid finalized block hash")
        header = self.call("chain_getHeader", [head])
        if not isinstance(header, dict) or not isinstance(header.get("number"), str):
            raise ChainRejected("Missing finalized header")
        try:
            number = int(header["number"], 16)
        except ValueError as exc:
            raise ChainRejected("Invalid finalized height") from exc
        if number < 0 or number > (2**64 - 1):
            raise ChainRejected("Finalized height outside uint64")
        return {**identity, "finalized_hash": head, "finalized_height": number,
                "mainnet_ready": False, "status": "DEVELOPMENT_NETWORK_ONLY"}

    def block_at_height(self, height: int):
        if type(height) is not int or height < 0 or height > (2**64 - 1):
            raise ChainRejected("Block number must be uint64")
        self.verify_identity()
        block_hash = self.call("chain_getBlockHash", [height])
        if block_hash is None:
            return None
        return self._fetch_block(block_hash, height)

    def _fetch_block(self, block_hash, height=None):
        if not valid_hash(block_hash):
            raise ChainRejected("Invalid block hash supplied by node")
        block = self.call("chain_getBlock", [block_hash])
        if not isinstance(block, dict) or not isinstance(block.get("block"), dict):
            raise ChainRejected("Malformed block data")
        header = block["block"].get("header")
        extrinsics = block["block"].get("extrinsics")
        if not isinstance(header, dict) or not isinstance(extrinsics, list):
            raise ChainRejected("Malformed header or extrinsics")
        if any(not isinstance(x, str) or not x.startswith("0x") or
               len(x) > 200_000 or len(x) % 2 != 0 for x in extrinsics):
            raise ChainRejected("Malformed SCALE extrinsic")
        try:
            found_height = int(header["number"], 16)
        except (ValueError, KeyError, TypeError) as exc:
            raise ChainRejected("Malformed block height") from exc
        if height is not None and found_height != height:
            raise ChainRejected("Block number does not match requested height")
        return {"hash": block_hash, "height": found_height,
                "header": header, "extrinsics_hex": extrinsics,
                "decoded_transactions": False, "finality_confirmed": False}

    def block_by_hash(self, block_hash):
        if not valid_hash(block_hash):
            raise ChainRejected("Invalid supplied block hash")
        self.verify_identity()
        return self._fetch_block(block_hash)
