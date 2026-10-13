"""Network identity guards for DEVNIRA local node monitoring.

No signing, key management or chain ownership is implied. An unpinned
upstream Quantus RPC endpoint must never be labelled a DVN company wallet.
"""
import re
from urllib.parse import urlsplit

HASH = re.compile(r"^0x[0-9a-fA-F]{64}$")

def validate_local_rpc(url: str) -> str:
    if not isinstance(url, str) or not url:
        raise ValueError("RPC endpoint required")
    parsed = urlsplit(url)
    if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost"):
        raise ValueError("Only local unencrypted HTTP RPC is permitted")
    if parsed.username or parsed.password or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise ValueError("RPC must not contain credentials, paths, query or fragments")
    if parsed.port is None or not (1 <= parsed.port <= 65535):
        raise ValueError("Explicit localhost RPC port required")
    return url

def validate_identity(chain: object, runtime: object, genesis: object, expected_genesis: str) -> None:
    if not isinstance(chain, str) or "devnira" not in chain.lower():
        raise ValueError("Connected chain is not identified as DEVNIRA")
    if not isinstance(runtime, dict) or "devnira" not in str(runtime.get("specName", "")).lower():
        raise ValueError("Connected runtime is not DEVNIRA")
    if not isinstance(expected_genesis, str) or not HASH.fullmatch(expected_genesis):
        raise ValueError("Pinned trusted DEVNIRA genesis hash is required")
    if not isinstance(genesis, str) or not HASH.fullmatch(genesis):
        raise ValueError("Node returned invalid genesis hash")
    if genesis.lower() != expected_genesis.lower():
        raise ValueError("Unexpected network genesis; refusing to mark as verified")
