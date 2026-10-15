"""Bounded, read-only DEVNIRA RPC explorer API for local development.

Run: DVN_RPC_URL=http://127.0.0.1:9944 DVN_GENESIS_HASH=0x... \\
     python3 -m services.explorer_api
Bind is loopback only. Put authenticated TLS/rate-limiting infrastructure in front
of this service before any external exposure; it is not an indexer.
"""
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from services.network_rpc import ChainRejected, GuardedRpc, NodeIdentity, valid_hash
from services.finalized_indexer import IndexRejected, index_status, lookup_block

_BLOCK = re.compile(r"/api/block/([0-9]{1,20})\Z")
_BY_HASH = re.compile(r"/api/hash/(0x[0-9a-fA-F]{64})\Z")
_IDX_BLOCK = re.compile(r"/api/index/block/([0-9]{1,19})\Z")
_IDX_HASH = re.compile(r"/api/index/hash/(0x[0-9a-fA-F]{64})\Z")


def query(rpc, path, indexed_db=None):
    # Persistent indexer is opt-in and read-only. It is not a decoded explorer.
    if path.startswith("/api/index/"):
        if indexed_db is None:
            return 404, {"error": "Finalized block database not configured"}
        if path == "/api/index/status":
            return 200, index_status(indexed_db)
        by_height = _IDX_BLOCK.fullmatch(path)
        by_hash = _IDX_HASH.fullmatch(path)
        if by_height:
            block = lookup_block(indexed_db, height=int(by_height[1]))
            return (200, block) if block is not None else (404, {"error":"Finalized block not indexed"})
        if by_hash:
            block = lookup_block(indexed_db, block_hash=by_hash[1])
            return (200, block) if block is not None else (404, {"error":"Finalized block not indexed"})
        return 404, {"error": "Unknown indexed explorer endpoint"}
    if path == "/api/status":
        return 200, rpc.finalized_status()
    match = _BLOCK.fullmatch(path)
    if match:
        height = int(match[1])
        result = rpc.block_at_height(height)
        return (200, result) if result is not None else (404, {"error": "Block not found"})
    match = _BY_HASH.fullmatch(path)
    if match and valid_hash(match[1]):
        return 200, rpc.block_by_hash(match[1])
    return 404, {"error": "Unknown read-only explorer endpoint"}


def handler_type(rpc, indexed_db=None):
    class ExplorerHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlsplit(self.path)
            if parsed.query or parsed.fragment:
                self._send(400, {"error": "Query strings are not supported"})
                return
            try:
                code, value = query(rpc, parsed.path, indexed_db)
            except (ChainRejected, IndexRejected, OSError, TimeoutError, ValueError):
                code, value = 503, {"error": "Verified DEVNIRA RPC unavailable or incompatible"}
            self._send(code, value)

        def _send(self, code, obj):
            data = json.dumps(obj, separators=(",", ":")).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            self._send(405, {"error": "Read-only API"})

        def log_message(self, fmt, *args):
            return

    return ExplorerHandler


def main():
    url = os.environ.get("DVN_RPC_URL", "http://127.0.0.1:9944")
    pinned = os.environ.get("DVN_GENESIS_HASH", "")
    identity = NodeIdentity(url, pinned)
    port = int(os.environ.get("DVN_EXPLORER_PORT", "8777"))
    if not 1 <= port <= 65535:
        raise ValueError("Invalid explorer port")
    # Loopback is deliberate, not a production web server. DB is read-only in API.
    indexed_db = os.environ.get("DVN_EXPLORER_DB")
    server = ThreadingHTTPServer(("127.0.0.1", port),
                                 handler_type(GuardedRpc(identity), indexed_db))
    print("DEVNIRA read-only DEVELOPMENT RPC explorer on 127.0.0.1:" + str(port))
    server.serve_forever()


if __name__ == "__main__":
    main()
