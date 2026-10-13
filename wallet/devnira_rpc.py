#!/usr/bin/env python3
"""DEVNIRA read-only RPC wallet diagnostic (not a signing wallet).

Never accepts private keys or seed phrases. Queries only public chain data.
"""
import argparse
import json
import urllib.request

def rpc(url: str, method: str, params=None):
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}).encode()
    req = urllib.request.Request(url, payload, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.load(response)
    if "error" in data:
        raise RuntimeError(data["error"])
    return data.get("result")

def main():
    parser = argparse.ArgumentParser(description="Read-only DEVNIRA node diagnostics")
    parser.add_argument("--rpc", default="http://127.0.0.1:9944")
    args = parser.parse_args()
    print(json.dumps({
        "chain": rpc(args.rpc, "system_chain"),
        "genesis_hash": rpc(args.rpc, "chain_getBlockHash", [0]),
        "runtime_version": rpc(args.rpc, "state_getRuntimeVersion"),
    }, indent=2))

if __name__ == "__main__":
    main()
