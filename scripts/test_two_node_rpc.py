#!/usr/bin/env python3
"""DEVNIRA two-node RPC synchronization and chain identity smoke test.

Read-only localhost RPCs only. This checks chain identity, shared genesis,
peering and common finalized hashes; it does NOT prove GPU mining, economic
consensus, valid PoW or the correctness of ZK proofs.
"""
import argparse
import json
import time
from urllib.request import Request, urlopen

from wallet.network_identity import validate_local_rpc, validate_identity

def rpc(url: str, method: str, params=None):
    validate_local_rpc(url)
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params or []}).encode()
    with urlopen(Request(url, body, headers={"Content-Type":"application/json"}), timeout=5) as response:
        reply = json.load(response)
    if "error" in reply:
        raise RuntimeError(f"{method}: {reply['error']}")
    return reply.get("result")

def snapshot(url: str, trusted_genesis: str):
    chain = rpc(url, "system_chain")
    runtime = rpc(url, "state_getRuntimeVersion")
    genesis = rpc(url, "chain_getBlockHash", [0])
    validate_identity(chain, runtime, genesis, trusted_genesis)
    head = rpc(url, "chain_getFinalizedHead")
    header = rpc(url, "chain_getHeader", [head])
    peers = rpc(url, "system_peers")
    return {"genesis": genesis, "finalized_hash": head,
            "finalized_height": int(header["number"], 16),
            "peer_count": len(peers) if isinstance(peers, list) else -1}

def assert_two_nodes(a: dict, b: dict, min_finalized_height: int=1):
    if a["genesis"].lower() != b["genesis"].lower():
        raise AssertionError("nodes have different genesis blocks")
    if a["peer_count"] < 1 or b["peer_count"] < 1:
        raise AssertionError("both nodes must have at least one peer")
    if a["finalized_height"] < min_finalized_height or b["finalized_height"] < min_finalized_height:
        raise AssertionError("finalized chain has not advanced")
    if a["finalized_height"] == b["finalized_height"] and a["finalized_hash"] != b["finalized_hash"]:
        raise AssertionError("forked finalized hashes at the same height")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--node-a", required=True)
    ap.add_argument("--node-b", required=True)
    ap.add_argument("--trusted-genesis", required=True, help="Independent known-good DVN genesis hash")
    ap.add_argument("--timeout-seconds", type=int, default=120)
    ap.add_argument("--min-finalized-height", type=int, default=1)
    args = ap.parse_args()
    if args.timeout_seconds <= 0 or args.min_finalized_height < 1:
        ap.error("timeout must be >0; minimum finalized height >=1")
    validate_local_rpc(args.node_a)
    validate_local_rpc(args.node_b)
    if args.node_a == args.node_b:
        ap.error("node A and node B must use different localhost endpoints")
    deadline = time.monotonic() + args.timeout_seconds
    last_error = None
    while time.monotonic() < deadline:
        try:
            a = snapshot(args.node_a, args.trusted_genesis)
            b = snapshot(args.node_b, args.trusted_genesis)
            assert_two_nodes(a, b, args.min_finalized_height)
            common_height = min(a["finalized_height"], b["finalized_height"])
            a_hash = rpc(args.node_a, "chain_getBlockHash", [common_height])
            b_hash = rpc(args.node_b, "chain_getBlockHash", [common_height])
            if not a_hash or a_hash != b_hash:
                raise AssertionError("nodes do not agree on common finalized chain")
            print("PASS: two locally connected DVN nodes share trusted genesis and a finalized block",
                  json.dumps({"height":common_height,"hash":a_hash}))
            return
        except (RuntimeError, ValueError, AssertionError, KeyError, OSError) as exc:
            last_error = exc
            time.sleep(2)
    raise SystemExit(f"FAIL: no verified two-node sync: {last_error}")

if __name__ == "__main__":
    main()
