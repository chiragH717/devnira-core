#!/usr/bin/env python3
"""Fail-closed REAL V2 custody/root/header consistency over two finalized peers.

For future *approved* V2-only testnet. Current DEV net has header mode FALSE,
so this must BLOCK there, even if old V1 zkTreeRoot field exists. No proof
verification or production Send.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from scripts.test_two_node_rpc import rpc
from scripts.dvn_finalized_history_check import inspect,compare_pair,HistoryFailure
from scripts.dvn_signed_transfer_acceptance import hash32,network_guard
from wallet.network_identity import validate_local_rpc,validate_identity

MASK=(1<<64)-1
P1=11400714785074694791
P2=14029467366897019727
P3=1609587929392839161
P4=9650029242287828579
P5=2870177450012600261

class V2RootRejected(ValueError):pass

def _rol(x,n):return ((x<<n)|(x>>(64-n)))&MASK
def _round(v,k):
    v=(v+k*P2)&MASK
    v=_rol(v,31)
    return v*P1&MASK
def xxh64(raw:bytes,seed:int=0)->int:
    """Portable xxHash64 used by FRAME Twox128/Twox64Concat storage keys."""
    i=0;n=len(raw)
    if n>=32:
        v1=(seed+P1+P2)&MASK;v2=(seed+P2)&MASK
        v3=seed&MASK;v4=(seed-P1)&MASK
        while i<=n-32:
            v1=_round(v1,int.from_bytes(raw[i:i+8],"little"));i+=8
            v2=_round(v2,int.from_bytes(raw[i:i+8],"little"));i+=8
            v3=_round(v3,int.from_bytes(raw[i:i+8],"little"));i+=8
            v4=_round(v4,int.from_bytes(raw[i:i+8],"little"));i+=8
        acc=(_rol(v1,1)+_rol(v2,7)+_rol(v3,12)+_rol(v4,18))&MASK
        for v in (v1,v2,v3,v4):
            mix=_round(0,v)
            acc=((acc^mix)*P1+P4)&MASK
    else:
        acc=(seed+P5)&MASK
    acc=(acc+n)&MASK
    while i+8<=n:
        k=_round(0,int.from_bytes(raw[i:i+8],"little"))
        acc=(_rol(acc^k,27)*P1+P4)&MASK
        i+=8
    if i+4<=n:
        acc=(_rol(acc^(int.from_bytes(raw[i:i+4],"little")*P1&MASK),23)*P2+P3)&MASK
        i+=4
    while i<n:
        acc=_rol(acc^(raw[i]*P5&MASK),11)*P1&MASK
        i+=1
    acc^=acc>>33
    acc=acc*P2&MASK
    acc^=acc>>29
    acc=acc*P3&MASK
    acc^=acc>>32
    return acc&MASK
def twox128(raw:bytes)->bytes:
    return xxh64(raw,0).to_bytes(8,"little")+xxh64(raw,1).to_bytes(8,"little")
def storage_prefix(pallet:str,name:str)->bytes:
    return twox128(pallet.encode())+twox128(name.encode())
def value_key(pallet:str,name:str)->str:
    return "0x"+storage_prefix(pallet,name).hex()
def history_key(height:int)->str:
    if type(height) is not int or not 0<=height<2**32:
        raise V2RootRejected("Only canonical SCALE u32 DEV heights supported")
    encoded=height.to_bytes(4,"little")
    return "0x"+(storage_prefix("Wormhole","DvnV2TreeHistory")+
                 xxh64(encoded).to_bytes(8,"little")+encoded).hex()
def raw_exact(value,expected:int,label:str)->bytes:
    if not isinstance(value,str) or not value.startswith("0x") or len(value)!=2+2*expected:
        raise V2RootRejected("Missing/invalid finalized "+label)
    try:return bytes.fromhex(value[2:])
    except ValueError as exc:raise V2RootRejected("Noncanonical hex "+label) from exc

def root_in_finalized_state(url:str,block_hash:str,height:int,transport=rpc)->dict:
    validate_local_rpc(url)
    h=hash32(block_hash,"finalized block")
    mode=transport(url,"state_getStorage",[value_key("System","DvnV2HeaderMode"),h])
    if mode!="0x01":
        raise V2RootRejected("INACTIVE: V2 consensus header selector disabled; V1 root not acceptable")
    root=raw_exact(transport(url,"state_getStorage",[value_key("Wormhole","DvnV2TreeRoot"),h]),
                   32,"independent V2 Merkle root")
    if not any(root):
        raise V2RootRejected("No nonempty V2 custody root")
    cnt=raw_exact(transport(url,"state_getStorage",[value_key("Wormhole","DvnV2TreeCount"),h]),
                  8,"custody V2 leaf count")
    count=int.from_bytes(cnt,"little")
    if not 1<=count<=1<<32:
        raise V2RootRejected("No real deposits or leaf cap violated")
    hist=raw_exact(transport(url,"state_getStorage",[history_key(height),h]),
                   40,"block-end V2 root history")
    if hist[:32]!=root or int.from_bytes(hist[32:],"little")!=count:
        raise V2RootRejected("V2 historical snapshot doesn't bind same root/count")
    header=transport(url,"chain_getHeader",[h])
    if not isinstance(header,dict) or int(header.get("number","-1"),16)!=height:
        raise V2RootRejected("Finalized header height not proven")
    if hash32(header.get("zkTreeRoot"),"header zkTreeRoot")!="0x"+root.hex():
        raise V2RootRejected("CRITICAL: independent custody root is not in finalized header")
    return {"height":height,"block_hash":h,"root":"0x"+root.hex(),
            "leaf_count":count,"header_v2_mode_active":True,
            "block_end_snapshot_matches":True}

def finalized_snapshot(url:str,genesis:str,transport=rpc)->dict:
    chain=transport(url,"system_chain")
    version=transport(url,"state_getRuntimeVersion")
    actual=transport(url,"chain_getBlockHash",[0])
    validate_identity(chain,version,actual,genesis)
    head=hash32(transport(url,"chain_getFinalizedHead"),"finalized peer head")
    header=transport(url,"chain_getHeader",[head])
    if not isinstance(header,dict) or not isinstance(header.get("number"),str):
        raise V2RootRejected("Missing finalized peer header")
    try:n=int(header["number"],16)
    except ValueError as exc:raise V2RootRejected("Malformed finalized peer height") from exc
    if n<1 or hash32(transport(url,"chain_getBlockHash",[n]))!=head:
        raise V2RootRejected("Finalized peer head is not canonical post-genesis")
    peers=transport(url,"system_peers")
    if not isinstance(peers,list) or not peers:
        raise V2RootRejected("No live connected P2P peer for V2 root history")
    return {"genesis":hash32(actual),"finalized_height":n,
            "finalized_hash":head,"peer_count":len(peers)}

def inspect_pair(a:str,b:str,genesis:str,height:int,*,depth:int=8,transport=rpc)->dict:
    if a==b:raise V2RootRejected("Two distinct peers required")
    # Mere RPC block existence is NOT finalized consensus evidence.
    # Bind the supplied trusted DEV genesis, runtime/8 decimals and peers
    # to both actual endpoints BEFORE touching custody storage.
    network_guard(a,b,genesis,transport)
    before_a=finalized_snapshot(a,genesis,transport)
    before_b=finalized_snapshot(b,genesis,transport)
    if min(before_a["finalized_height"],before_b["finalized_height"])<height:
        raise V2RootRejected("Requested V2 root height was NOT finalized by both peers")
    pa=inspect(a,genesis,height,depth=depth,transport=transport)
    pb=inspect(b,genesis,height,depth=depth,transport=transport)
    try:compare_pair(pa,pb)
    except HistoryFailure as exc:raise V2RootRejected("Finalized ancestry mismatch") from exc
    lines=[];last_count=None
    for key in sorted(pa["records"],key=int):
        n=int(key);h=pa["records"][key]["hash"]
        x=root_in_finalized_state(a,h,n,transport)
        y=root_in_finalized_state(b,h,n,transport)
        if x!=y:raise V2RootRejected("V2 root/storage mismatch across independent peers")
        if last_count is not None and x["leaf_count"]<last_count:
            raise V2RootRejected("V2 custody leaf count regressed in finalized history")
        last_count=x["leaf_count"]
        lines.append(x)
    # Protect against one RPC silently switching canonical data during read.
    after_a=finalized_snapshot(a,genesis,transport)
    after_b=finalized_snapshot(b,genesis,transport)
    if (min(after_a["finalized_height"],after_b["finalized_height"])<height
        or min(after_a["finalized_height"],after_b["finalized_height"])<
           min(before_a["finalized_height"],before_b["finalized_height"])
        or hash32(transport(a,"chain_getBlockHash",[height]))!=pa["records"][str(height)]["hash"]
        or hash32(transport(b,"chain_getBlockHash",[height]))!=pb["records"][str(height)]["hash"]):
        raise V2RootRejected("DEV finalized V2 ancestry changed during evidence capture")
    return {"schema":"devnira-v2-actual-header-custody-root-audit-v1",
            "network":"LOCAL DEV ONLY; must NOT use current default-disabled chain",
            "roots_derived_from_REAL_finalized_wormhole_storage":True,
            "both_nodes_identical":True,"history":lines,
            "approved_production_vk":False,
            "membership_witness_reverified":False,
            "secure_proof_settlement_tested":False,"mainnet_ready":False}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--node-a",default="http://127.0.0.1:19541")
    p.add_argument("--node-b",default="http://127.0.0.1:19542")
    p.add_argument("--trusted-genesis",required=True)
    p.add_argument("--height",required=True,type=int)
    p.add_argument("--depth",type=int,default=8)
    p.add_argument("--json-out",required=True,type=Path)
    x=p.parse_args()
    report=inspect_pair(x.node_a,x.node_b,x.trusted_genesis,x.height,depth=x.depth)
    x.json_out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("Actual finalized V2 custody root matched headers/storage; STILL NOT SEND/MAINNET")
if __name__=="__main__":main()
