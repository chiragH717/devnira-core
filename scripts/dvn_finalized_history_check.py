#!/usr/bin/env python3
"""Independent RPC cross-check of DEVELOPMENT finalized header ancestry.

Reads REAL RPCs from 2 independent local nodes; all hashes must agree at
each indexed height and parent linkage must connect to the canonical chain.
Does NOT recompute Poseidon hash, prove consensus, V2 witness validity,
activate approved V2 keys, or permit production Send.
"""
from __future__ import annotations
import re
from scripts.test_two_node_rpc import rpc,snapshot

HEX32=re.compile(r"0x[0-9a-fA-F]{64}\Z")
class HistoryFailure(ValueError):pass

def hex32(value):
    if not isinstance(value,str) or not HEX32.fullmatch(value):
        raise HistoryFailure("Invalid, absent or non-32-byte chain hash")
    return value.lower()

def inspect(url:str, trusted_genesis:str, finalized_height:int, *,
            depth:int=8, transport=rpc)->dict:
    if type(finalized_height) is not int or finalized_height<1:
        raise HistoryFailure("Genesis-only history is not finalized transaction evidence")
    if type(depth) is not int or not 1<=depth<=64:
        raise HistoryFailure("Invalid bounded ancestry depth")
    genesis=hex32(trusted_genesis)
    if genesis=="0x"+"0"*64:
        raise HistoryFailure("All-zero development genesis forbidden")
    end=max(1,finalized_height-depth+1)
    records={}
    expected=None
    for n in range(finalized_height,end-1,-1):
        h=hex32(transport(url,"chain_getBlockHash",[n]))
        if expected is not None and expected!=h:
            raise HistoryFailure("Noncanonical ancestor hash/parent mismatch at "+str(n))
        head=transport(url,"chain_getHeader",[h])
        if not isinstance(head,dict):
            raise HistoryFailure("Missing finalized historical header")
        try:
            number=int(head.get("number"),16)
        except (ValueError,TypeError):
            raise HistoryFailure("Bad historical block number")
        if number!=n:
            raise HistoryFailure("Header number does not match canonical height")
        parent=hex32(head.get("parentHash"))
        state=hex32(head.get("stateRoot"))
        extrinsics=hex32(head.get("extrinsicsRoot"))
        zk=hex32(head.get("zkTreeRoot"))
        if not isinstance(head.get("digest"),dict):
            raise HistoryFailure("Missing historical header digest")
        prev=hex32(transport(url,"chain_getBlockHash",[n-1]))
        if parent!=prev:
            raise HistoryFailure("Broken canonical parent linkage at "+str(n))
        if n==1 and prev!=genesis:
            raise HistoryFailure("Ancestry fork does not descend from trusted DEV genesis")
        expected=parent
        records[str(n)]={"hash":h,"number":n,"parent":parent,
                          "state_root":state,"extrinsics_root":extrinsics,
                          "zk_tree_root":zk,"digest":head["digest"]}
    return {"genesis":genesis,"top":finalized_height,"oldest":end,
            "records":records,"root_field_is_production_v2_activated":False}

def compare_pair(a:dict,b:dict)->dict:
    if a["genesis"]!=b["genesis"] or a["top"]!=b["top"] or a["oldest"]!=b["oldest"]:
        raise HistoryFailure("Independent nodes disagree on genesis or requested finalized window")
    if a["records"]!=b["records"]:
        raise HistoryFailure("Independent nodes disagree on finalized ancestry or header root")
    if not a["records"]:
        raise HistoryFailure("No non-genesis finalized header proof")
    return {"height":a["top"],"count":len(a["records"]),
            "oldest":a["oldest"],"same_canonical_history":True,
            "all_headers_have_zk_root":True}

def compare_restart(before:dict,after:dict)->dict:
    if before!=after:
        raise HistoryFailure("Persisted finalized history mutated after node restart")
    return {"preserved_blocks":len(before["records"]),
            "canonical_parent_links_preserved":True,
            "historic_header_roots_preserved":True}

def paired_rpc_audit(url_a:str,url_b:str,genesis:str,height:int)->dict:
    if url_a==url_b:
        raise HistoryFailure("Cannot compare identical endpoint twice")
    s1=snapshot(url_a,genesis)
    s2=snapshot(url_b,genesis)
    if min(s1["peer_count"],s2["peer_count"])<1:
        raise HistoryFailure("Both real nodes must be connected")
    if min(s1["finalized_height"],s2["finalized_height"])<height:
        raise HistoryFailure("Requested ancestry includes unfinalized blocks")
    a=inspect(url_a,genesis,height)
    b=inspect(url_b,genesis,height)
    return {"summary":compare_pair(a,b),"history":a}
