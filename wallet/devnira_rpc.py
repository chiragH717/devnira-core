#!/usr/bin/env python3
"""DEVNIRA public-account diagnostic, not a signing or transaction wallet.

Every RPC call is limited to localhost. A *trusted independent genesis hash*
is mandatory; no upstream Quantus development network may look like live DVN.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wallet.devnira_balance import format_dvn, read_finalized_balance, rpc
from wallet.network_identity import HASH, validate_identity, validate_local_rpc

def diagnostics(endpoint: str, trusted_genesis: str, address: str | None = None,
                *, rpc_fn=rpc) -> dict:
    validate_local_rpc(endpoint)
    if not isinstance(trusted_genesis, str) or not HASH.fullmatch(trusted_genesis):
        raise ValueError("A independently trusted DEVNIRA genesis hash is mandatory")
    chain = rpc_fn(endpoint, "system_chain")
    genesis = rpc_fn(endpoint, "chain_getBlockHash", [0])
    version = rpc_fn(endpoint, "state_getRuntimeVersion")
    validate_identity(chain, version, genesis, trusted_genesis)
    if version.get("specName") != "devnira-runtime":
        raise ValueError("Unexpected runtime specName")
    props = rpc_fn(endpoint, "system_properties")
    if not isinstance(props, dict) or (
        props.get("tokenSymbol"),props.get("tokenDecimals"),props.get("ss58Format")
    ) != ("DVN",8,190):
        raise ValueError("Network properties do not identify eight-decimal DVN")
    info={
        "chain":chain,
        "genesis_hash":genesis,
        "runtime_version":version,
        "warning":"Read-only preview. Local RPC is not independently authenticated.",
    }
    if address:
        result=read_finalized_balance(
            endpoint,trusted_genesis,address,rpc_fn=rpc_fn
        )
        info["account"]={
            "public_address":result.address,
            "free":format_dvn(result.free_units),
            "reserved":format_dvn(result.reserved_units),
            "nonce":result.nonce,
            "finalized_block_hash":result.at_finalized_hash,
        }
    return info

def main():
    parser=argparse.ArgumentParser(description="DEVNIRA public balance diagnostic, not a signing wallet")
    parser.add_argument("--rpc",default="http://127.0.0.1:9944")
    parser.add_argument("--trusted-genesis",required=True,help="Previously independently verified 0x-prefixed 32-byte genesis hash")
    parser.add_argument("--account",help="Optional native SS58 190 public receiving address")
    args=parser.parse_args()
    print(json.dumps(diagnostics(args.rpc,args.trusted_genesis,args.account),indent=2))

if __name__=="__main__":
    main()
