#!/usr/bin/env python3
"""Two REAL development nodes: bidirectional P2P, finalized header root, restart.

No wallet keys are created or imported. No signed transfer, PoW, V2 production
finality or proof settlement is implied. This CI MUST fail, not invent success,
if the independent DEV nodes never finalize a post-genesis block.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.dvn_two_native_processes import start,stop,address,PeerFailure
from scripts.test_two_node_rpc import rpc, snapshot
from scripts.dvn_finalized_history_check import paired_rpc_audit,compare_restart
from wallet.network_identity import validate_identity

HEX32=re.compile(r"0x[0-9a-fA-F]{64}\Z")
DEV_SPEC="devnira-8dec-native-dev-test-runtime"
DEV_TOKEN=(8,"DVN",190)

def checked_header(raw:object,height:int)->dict:
    if not isinstance(raw,dict):
        raise PeerFailure("Missing actual RPC finalized block header")
    if type(height) is not int or height<1:
        raise PeerFailure("Never accept genesis-only as post-genesis finality")
    if not isinstance(raw.get("number"),str) or int(raw["number"],16)!=height:
        raise PeerFailure("Finalized header height disagrees with hash lookup")
    for field in ("parentHash","stateRoot","extrinsicsRoot","zkTreeRoot"):
        if not isinstance(raw.get(field),str) or not HEX32.fullmatch(raw[field]):
            raise PeerFailure("Missing or malformed canonical header component: "+field)
    if not isinstance(raw.get("digest"),dict):
        raise PeerFailure("Invalid finalized header digest")
    return {field:raw[field].lower() for field in
            ("parentHash","stateRoot","extrinsicsRoot","zkTreeRoot")}

def assess_pair(left:dict,right:dict,hash_left:str,hash_right:str,
                hdr_left:dict,hdr_right:dict)->dict:
    if left.get("genesis")!=right.get("genesis"):
        raise PeerFailure("Independent dev genesis mismatch")
    genesis=left.get("genesis")
    if not isinstance(genesis,str) or not HEX32.fullmatch(genesis) or genesis.lower()=="0x"+"0"*64:
        raise PeerFailure("Empty/invalid development genesis")
    if min(left.get("peer_count",-1),right.get("peer_count",-1))<1:
        raise PeerFailure("Two real nodes MUST be bidirectionally connected")
    n=min(left.get("finalized_height",-1),right.get("finalized_height",-1))
    if type(n) is not int or n<1:
        raise PeerFailure("No shared finalized post-genesis block yet")
    if any(not isinstance(x,str) or not HEX32.fullmatch(x) for x in (hash_left,hash_right)):
        raise PeerFailure("Missing finalized common-height block hash")
    if hash_left.lower()!=hash_right.lower():
        raise PeerFailure("Forked canonical finalized block hash at shared height")
    lh=checked_header(hdr_left,n)
    rh=checked_header(hdr_right,n)
    if lh!=rh:
        raise PeerFailure("Finalized block-header V2-root/state/digest data disagree")
    if left["finalized_height"]==right["finalized_height"]:
        if left.get("finalized_hash","").lower()!=right.get("finalized_hash","").lower():
            raise PeerFailure("Equal-height finalized tips disagree")
    return {"height":n,"hash":hash_left.lower(),"genesis":genesis.lower(),
            "header":lh,"zk_root":lh["zkTreeRoot"]}

def restart_existing(exe:Path,base:Path,boot:str):
    """Restart using original on-disk state, never call first-start mkdir()."""
    if not base.is_dir() or base.is_symlink():
        raise PeerFailure("Cannot restart without existing real node database directory")
    argv=[str(exe),"--base-path",str(base),"--port","31542",
          "--no-telemetry","--experimental-rpc-endpoint",
          "listen-addr=127.0.0.1:19542,methods=unsafe,cors=all",
          "--chain","dev","--bootnodes",boot]
    # Append instead of truncating node logs; preserve first-run evidence.
    with (base/"node.log").open("ab") as log:
        return subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL)

def identity(url:str,expected_genesis:str|None=None)->str:
    chain=rpc(url,"system_chain")
    version=rpc(url,"state_getRuntimeVersion")
    gen=rpc(url,"chain_getBlockHash",[0])
    props=rpc(url,"system_properties")
    validate_identity(chain,version,gen,expected_genesis or gen)
    if version.get("specName")!=DEV_SPEC:
        raise PeerFailure("Wrong isolated native 8-decimal DEV runtime")
    if (not isinstance(props,dict) or
        (props.get("tokenDecimals"),props.get("tokenSymbol"),props.get("ss58Format"))!=DEV_TOKEN):
        raise PeerFailure("Wrong token identity, precision or SS58 prefix")
    return gen

def await_identity(proc,url:str,deadline:float,expected:str|None=None)->str:
    error=None
    while time.monotonic()<deadline:
        if proc.poll() is not None:
            raise PeerFailure("Actual native node process exited")
        try:
            return identity(url,expected)
        except (PeerFailure,OSError,ValueError,KeyError,TypeError,RuntimeError) as exc:
            error=exc
            time.sleep(2)
    raise PeerFailure("DEV RPC identity/startup timed out: "+str(error))

def common(url_a:str,url_b:str,genesis:str)->dict:
    a=snapshot(url_a,genesis)
    b=snapshot(url_b,genesis)
    n=min(a["finalized_height"],b["finalized_height"])
    if n<1:
        raise PeerFailure("No post-genesis finalized block to authenticate")
    h1=rpc(url_a,"chain_getBlockHash",[n])
    h2=rpc(url_b,"chain_getBlockHash",[n])
    return assess_pair(a,b,h1,h2,
        rpc(url_a,"chain_getHeader",[h1]),rpc(url_b,"chain_getHeader",[h2]))

def wait_common(a,b,proc_a,proc_b,genesis:str,deadline:float)->dict:
    error=None
    while time.monotonic()<deadline:
        if proc_a.poll() is not None or proc_b.poll() is not None:
            raise PeerFailure("Actual native node stopped during sync/finality")
        try: return common(a,b,genesis)
        except (PeerFailure,OSError,ValueError,KeyError,RuntimeError,TypeError) as exc:
            error=exc
            time.sleep(3)
    raise PeerFailure("Real P2P/shared finalized header acceptance failed: "+str(error))

def run(binary:Path,timeout:int=270)->dict:
    exe=Path(binary).resolve(strict=True)
    if not exe.is_file() or not 60<=timeout<=900:
        raise PeerFailure("Actual native executable and timeout 60..900s required")
    ua,ub="http://127.0.0.1:19541","http://127.0.0.1:19542"
    a=b=None
    with tempfile.TemporaryDirectory(prefix="dvn-prewallet-live-two-node-") as tmp:
        root=Path(tmp)
        deadline=time.monotonic()+timeout
        try:
            a=start(exe,root/"node_a",31541,19541,dev=True)
            genesis=await_identity(a,ua,deadline)
            peer=rpc(ua,"system_localPeerId")
            b=start(exe,root/"node_b",31542,19542,boot=address(peer))
            await_identity(b,ub,deadline,genesis)
            first=wait_common(ua,ub,a,b,genesis,deadline)
            before_history=paired_rpc_audit(ua,ub,genesis,first["height"])
            # Stop second actual process; preserve its REAL database. Rejoin.
            stop(b);b=None
            b=restart_existing(exe,root/"node_b",address(peer))
            await_identity(b,ub,deadline,genesis)
            second=wait_common(ua,ub,a,b,genesis,deadline)
            if second["height"]<first["height"]:
                raise PeerFailure("Finality regressed after restarting second node")
            stable=rpc(ub,"chain_getBlockHash",[first["height"]])
            if stable.lower()!=first["hash"]:
                raise PeerFailure("Restart rewrote previously finalized block")
            h=checked_header(rpc(ub,"chain_getHeader",[stable]),first["height"])
            if h!=first["header"]:
                raise PeerFailure("Restart altered previously finalized V2 header-root preimage")
            after_history=paired_rpc_audit(ua,ub,genesis,first["height"])
            persisted=compare_restart(before_history["history"],after_history["history"])
            return {
                "schema":"devnira-real-prewallet-devnet-finalized-ancestry-v2",
                "classification":"ISOLATED DEVELOPMENT: NOT PRODUCTION OR SIGNED SEND",
                "actual_native_processes":2,"bidirectional_p2p":True,
                "actual_non_genesis_finalized_header_consistent":True,
                "native_header_root_field_checked":True,
                "node_2_restart_with_same_database_verified":True,
                "shared_dev_genesis":genesis,
                "first_finalized":first,"after_restart":second,
                "historical_ancestry_cross_node":before_history["summary"],
                "persisted_history_after_node_restart":persisted,
                "v2_header_mode_active":False,
                "full_production_v2_witness_history_verified":False,
                "signed_extrinsic_submitted":False,
                "gpu_qpow_validated":False,"active_zk_v2":False,
                "production_fixed_vk_approved":False,
                "independent_mainnet_genesis":False,
                "mainnet_ready":False
            }
        except (PeerFailure,OSError,ValueError,KeyError,RuntimeError,TypeError):
            for name in ("node_a","node_b"):
                f=root/name/"node.log"
                if f.exists():
                    print(name+" last log lines:\n"+f.read_bytes()[-6000:].decode(errors="replace"),
                          file=sys.stderr)
            raise
        finally:
            stop(b);stop(a)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--node",required=True,type=Path)
    p.add_argument("--json",required=True,type=Path)
    p.add_argument("--timeout",type=int,default=270)
    a=p.parse_args()
    result=run(a.node,a.timeout)
    a.json.parent.mkdir(parents=True,exist_ok=True)
    a.json.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("PASS: actual DEV nodes, canonical history and zk header roots after restart (NO ACTIVE V2/SEND)")
if __name__=="__main__":
    main()
