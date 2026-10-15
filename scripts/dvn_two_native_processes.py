#!/usr/bin/env python3
"""Run two REAL localhost native DVN research nodes and verify actual P2P.

Never implies validated GPU work, signed Send, independent Genesis or mainnet.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time
from scripts.test_two_node_rpc import rpc, snapshot
from wallet.network_identity import validate_identity

class PeerFailure(RuntimeError):
    pass

def check(a,b):
    if a["genesis"].lower()!=b["genesis"].lower():
        raise PeerFailure("Different development genesis")
    if min(a["peer_count"],b["peer_count"]) < 1:
        raise PeerFailure("Bidirectional real P2P connections missing")
    if a["finalized_height"]==b["finalized_height"] and a["finalized_hash"]!=b["finalized_hash"]:
        raise PeerFailure("Different finalized blocks at same height")

def address(peer):
    if not isinstance(peer,str) or not re.fullmatch(r"[A-Za-z0-9]{20,4096}",peer):
        raise PeerFailure("Unsafe native peer id")
    return "/ip4/127.0.0.1/tcp/31541/p2p/"+peer

def start(exe,base,port,rpcport,*,dev=False,boot=None):
    base.mkdir(mode=0o700)
    command=[str(exe),"--base-path",str(base),"--port",str(port),
             "--no-telemetry","--experimental-rpc-endpoint",
             f"listen-addr=127.0.0.1:{rpcport},methods=unsafe,cors=all"]
    command+=["--dev"] if dev else ["--chain","dev"]
    if boot: command+=["--bootnodes",boot]
    with (base/"node.log").open("wb") as log:
        return subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)

def stop(proc):
    if proc and proc.poll() is None:
        proc.terminate()
        try: proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill();proc.wait(timeout=10)

def identified(url,expect=None):
    chain=rpc(url,"system_chain")
    version=rpc(url,"state_getRuntimeVersion")
    genesis=rpc(url,"chain_getBlockHash",[0])
    props=rpc(url,"system_properties")
    validate_identity(chain,version,genesis,expect or genesis)
    if version.get("specName")!="devnira-8dec-inert-dev-runtime":
        raise PeerFailure("Wrong runtime — inert research only")
    if not isinstance(props,dict) or (
        props.get("tokenDecimals"),props.get("tokenSymbol"),props.get("ss58Format"))!=(8,"DVN",190):
        raise PeerFailure("Wrong network properties")
    return genesis

def await_identity(proc,url,deadline,expect=None):
    last=None
    while time.monotonic()<deadline:
        if proc.poll() is not None: raise PeerFailure("Native node failed to start")
        try: return identified(url,expect)
        except (OSError,ValueError,KeyError,RuntimeError,TypeError) as e:
            last=e;time.sleep(2)
    raise PeerFailure(f"Node startup timed out: {last}")

def run(node,timeout=180):
    exe=Path(node).resolve(strict=True)
    if not exe.is_file() or not 20<=timeout<=900:
        raise PeerFailure("Native binary and valid timeout required")
    a=b=None
    with tempfile.TemporaryDirectory(prefix="devnira-two-real-nodes-") as temp:
        root=Path(temp)
        ua="http://127.0.0.1:19541"
        ub="http://127.0.0.1:19542"
        deadline=time.monotonic()+timeout
        try:
            a=start(exe,root/"node_a",31541,19541,dev=True)
            genesis=await_identity(a,ua,deadline)
            peer=rpc(ua,"system_localPeerId")
            b=start(exe,root/"node_b",31542,19542,boot=address(peer))
            await_identity(b,ub,deadline,genesis)
            last=None
            while time.monotonic()<deadline:
                if a.poll() is not None or b.poll() is not None:
                    raise PeerFailure("Actual native process stopped prematurely")
                try:
                    sa=snapshot(ua,genesis);sb=snapshot(ub,genesis)
                    check(sa,sb)
                    height=min(sa["finalized_height"],sb["finalized_height"])
                    ha=rpc(ua,"chain_getBlockHash",[height])
                    hb=rpc(ub,"chain_getBlockHash",[height])
                    if not ha or ha.lower()!=hb.lower():
                        raise PeerFailure("Common finalized chain hash mismatch")
                    return {"schema":"dvn-two-actual-native-processes-p2p-v1",
                            "actual_native_processes":2,"bidirectional_p2p":True,
                            "shared_dev_genesis":genesis,"common_finalized_height":height,
                            "common_finalized_hash":ha,"gpu_mining_verified":False,
                            "signed_transfers_verified":False,"active_v2_verified":False,
                            "production_genesis":False,"mainnet_ready":False}
                except (OSError,ValueError,KeyError,RuntimeError,TypeError) as e:
                    last=e;time.sleep(2)
            raise PeerFailure(f"Real P2P peer handshake failed: {last}")
        except (PeerFailure,OSError):
            for name in ("node_a","node_b"):
                log=root/name/"node.log"
                if log.exists():
                    print(name+" logs:\n"+log.read_bytes()[-4000:].decode(errors="replace"))
            raise
        finally:
            stop(b);stop(a)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--node",type=Path,required=True)
    p.add_argument("--json",type=Path,required=True)
    p.add_argument("--timeout",type=int,default=180)
    args=p.parse_args()
    report=run(args.node,args.timeout)
    args.json.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("PASS: two actual native dev nodes peered; no GPU/mining/send proven")
if __name__=="__main__":main()
