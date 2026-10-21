#!/usr/bin/env python3
"""Production-denying DEV-only REAL signed Dilithium extrinsic acceptance probe.

No signer/private key/seed handling. The unsigned-input source is FORBIDDEN:
only an already-signed SCALE extrinsic file from a separate offline DEV signer
may be used. A signed extrinsic is public, but MUST NEVER contain real funds.
No proof of active ZK V2 or mainnet. No acceptance without observed finalized
balance/nonce/issuance effects, two-peer agreement and replay rejection.
"""
from __future__ import annotations
import argparse
from hashlib import blake2b
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError

from spec.ss58_company_account import decode_ss58_account
from scripts.test_two_node_rpc import rpc, snapshot
from wallet.network_identity import validate_local_rpc

HEX32=re.compile(r"0x[0-9a-fA-F]{64}\Z")
HEX_BYTES=re.compile(r"0x(?:[0-9a-fA-F]{2})+\Z")
SYSTEM_ACCOUNT_PREFIX=bytes.fromhex(
    "26aa394eea5630e07c48ae0c9558cef7b99d880ec681799c0cf30e8886371da9"
)
TOTAL_ISSUANCE_KEY=("0xc2261276cc9d1f8598ea4b6a74b15c2f"
                    "57c875e4cff74148e4628f264b974c80")
RUNTIME_SPEC="devnira-8dec-native-dev-test-runtime"

class SignedTransferFailure(ValueError):pass

def hash32(value, label="hash"):
    if not isinstance(value,str) or not HEX32.fullmatch(value):
        raise SignedTransferFailure("Malformed "+label)
    return value.lower()

def account_key(account_ss58:str)->str:
    account=decode_ss58_account(account_ss58,190)
    return "0x"+(SYSTEM_ACCOUNT_PREFIX+blake2b(account,digest_size=16).digest()+account).hex()

def read_account(raw)->dict:
    if raw is None:
        return dict(nonce=0,free=0,reserved=0,frozen=0,flags=0)
    if not isinstance(raw,str) or len(raw)!=162 or not HEX_BYTES.fullmatch(raw):
        raise SignedTransferFailure("Wrong SCALE AccountInfo<u32, AccountData<u128>> length")
    b=bytes.fromhex(raw[2:])
    return dict(nonce=int.from_bytes(b[0:4],"little"),
                free=int.from_bytes(b[16:32],"little"),
                reserved=int.from_bytes(b[32:48],"little"),
                frozen=int.from_bytes(b[48:64],"little"),
                flags=int.from_bytes(b[64:80],"little"))

def read_issuance(raw)->int:
    if not isinstance(raw,str) or len(raw)!=34 or not HEX_BYTES.fullmatch(raw):
        raise SignedTransferFailure("Missing 16-byte native Balances.TotalIssuance")
    return int.from_bytes(bytes.fromhex(raw[2:]),"little")

def state_at(url:str,block_hash:str,from_key:str,to_key:str,transport=rpc)->dict:
    h=hash32(block_hash,"finalized state hash")
    return {
        "sender":read_account(transport(url,"state_getStorage",[from_key,h])),
        "recipient":read_account(transport(url,"state_getStorage",[to_key,h])),
        "issuance":read_issuance(transport(url,"state_getStorage",[TOTAL_ISSUANCE_KEY,h]))
    }

def check_transition(before:dict,after:dict,amount:int, *, min_fee:int=1)->dict:
    if type(amount) is not int or not 1<=amount<=10_000_000_000_000_000:
        raise SignedTransferFailure("Invalid exact 8-decimal base-unit transfer amount")
    if type(min_fee) is not int or min_fee<0:
        raise SignedTransferFailure("Invalid minimum native fee")
    old_s,new_s=before["sender"],after["sender"]
    old_r,new_r=before["recipient"],after["recipient"]
    if old_s["nonce"]+1!=new_s["nonce"]:
        raise SignedTransferFailure("Nonce was not increased by exactly one finalized transaction")
    if any(new_s[k]!=old_s[k] for k in ("reserved","frozen","flags")):
        raise SignedTransferFailure("Unexpected sender reserved/frozen/flags change")
    if any(new_r[k]!=old_r[k] for k in ("nonce","reserved","frozen","flags")):
        raise SignedTransferFailure("Unexpected recipient nonce/locks/flags change")
    if new_r["free"]-old_r["free"]!=amount:
        raise SignedTransferFailure("Receiver not credited exactly the signed base-unit amount")
    debit=old_s["free"]-new_s["free"]
    fee=debit-amount
    if fee<min_fee:
        raise SignedTransferFailure("Sender debit does not conserve transfer and native fee")
    if before["issuance"]!=after["issuance"]:
        raise SignedTransferFailure("Native total issuance changed in a simple signed transfer")
    return {"exact_base_units":amount,"sender_debit_units":debit,
            "recipient_credit_units":amount,"finalized_fee_units":fee,
            "nonce_before":old_s["nonce"],"nonce_after":new_s["nonce"],
            "issuance_unchanged":True}

def network_guard(a,b,genesis,transport=rpc):
    if a==b:
        raise SignedTransferFailure("Cannot validate one endpoint as two independent nodes")
    for url in (a,b):
        validate_local_rpc(url)
        version=transport(url,"state_getRuntimeVersion")
        props=transport(url,"system_properties")
        actual=hash32(transport(url,"chain_getBlockHash",[0]),"DEV genesis")
        if (not isinstance(version,dict) or version.get("specName")!=RUNTIME_SPEC
                or actual!=hash32(genesis,"trusted DEV genesis")
                or not isinstance(props,dict)
                or (props.get("tokenDecimals"),props.get("tokenSymbol"),
                    props.get("ss58Format"))!=(8,"DVN",190)):
            raise SignedTransferFailure("Incorrect isolated native 8-decimal DEV chain")
        peers=transport(url,"system_peers")
        if not isinstance(peers,list) or not peers:
            raise SignedTransferFailure("Two actual connected DEV peers required")

def transaction_hex(content:str)->str:
    value=content.strip()
    if not HEX_BYTES.fullmatch(value) or not 10<=len(value)<=327680:
        raise SignedTransferFailure("Missing complete previously signed SCALE extrinsic bytes")
    b=bytes.fromhex(value[2:])
    tag=b[0]&3
    if tag==0:
        size,offset=b[0]>>2,1
    elif tag==1:
        if len(b)<2:raise SignedTransferFailure("Truncated compact SCALE size")
        size,offset=int.from_bytes(b[:2],"little")>>2,2
    elif tag==2:
        if len(b)<4:raise SignedTransferFailure("Truncated compact SCALE size")
        size,offset=int.from_bytes(b[:4],"little")>>2,4
    else:
        n=(b[0]>>2)+4
        if n>8 or len(b)<1+n:
            raise SignedTransferFailure("Oversized compact SCALE length prefix")
        size,offset=int.from_bytes(b[1:1+n],"little"),1+n
    if size!=len(b)-offset or offset>=len(b):
        raise SignedTransferFailure("SCALE extrinsic length mismatch")
    if b[offset]&0x80==0 or (b[offset]&0x7f) not in (4,5):
        raise SignedTransferFailure("Unsigned or unsupported transaction version")
    return value.lower()

def finalized_inclusion(url_a,url_b,genesis,tx_hash,before_height,
                        deadline,transport=rpc):
    candidate=hash32(tx_hash,"submitted extrinsic hash")
    previous=before_height
    while time.monotonic()<deadline:
        ha=hash32(transport(url_a,"chain_getFinalizedHead"),"node A finalized tip")
        hb=hash32(transport(url_b,"chain_getFinalizedHead"),"node B finalized tip")
        na=int(transport(url_a,"chain_getHeader",[ha])["number"],16)
        nb=int(transport(url_b,"chain_getHeader",[hb])["number"],16)
        top=min(na,nb)
        if top<=before_height:
            time.sleep(2);continue
        for number in range(max(previous+1,before_height+1),top+1):
            at=hash32(transport(url_a,"chain_getBlockHash",[number]),"canonical block")
            bt=hash32(transport(url_b,"chain_getBlockHash",[number]),"peer canonical block")
            if at!=bt:
                raise SignedTransferFailure("Finalized peers disagree on included block hash")
            block=transport(url_a,"chain_getBlock",[at])
            block_b=transport(url_b,"chain_getBlock",[bt])
            if not isinstance(block,dict) or not isinstance(block_b,dict):
                raise SignedTransferFailure("No actual finalized block body")
            extrinsics=block.get("block",{}).get("extrinsics")
            peer_extrinsics=block_b.get("block",{}).get("extrinsics")
            if not isinstance(extrinsics,list) or extrinsics!=peer_extrinsics:
                raise SignedTransferFailure("Peers disagree on finalized block body")
            hashes=[]
            for ext in extrinsics:
                if not isinstance(ext,str) or not HEX_BYTES.fullmatch(ext):
                    raise SignedTransferFailure("Bad full SCALE extrinsic in finalized block")
                hashes.append("0x"+blake2b(bytes.fromhex(ext[2:]),digest_size=32).hexdigest())
            if candidate in hashes:
                return {"block_hash":at,"block_number":number,
                        "extrinsic_index":hashes.index(candidate),
                        "extrinsic_hash":candidate,
                        "both_nodes_identical_finalized_body":True}
        previous=top
        time.sleep(2)
    raise SignedTransferFailure("No signed extrinsic in any shared finalized block before timeout")

def accept_dev_transfer(*, node_a,node_b,trusted_genesis,from_ss58,to_ss58,
                        amount_units,signed_hex,timeout=120,transport=rpc)->dict:
    if not 10<=timeout<=900:
        raise SignedTransferFailure("Timeout must be 10..900 seconds")
    if from_ss58==to_ss58:
        raise SignedTransferFailure("Sender cannot be recipient in conservation acceptance")
    if type(amount_units) is not int:
        raise SignedTransferFailure("Integer 8-decimal base units required")
    network_guard(node_a,node_b,trusted_genesis,transport)
    from_key,to_key=account_key(from_ss58),account_key(to_ss58)
    if from_key==to_key:
        raise SignedTransferFailure("Duplicated sender/receiver AccountId")
    sender_ext=transaction_hex(signed_hex)
    before_a=hash32(transport(node_a,"chain_getFinalizedHead"),"before finalized")
    before_b=hash32(transport(node_b,"chain_getFinalizedHead"),"before finalized peer")
    if before_a!=before_b:
        raise SignedTransferFailure("Peers did not start from the identical finalized state")
    before_height=int(transport(node_a,"chain_getHeader",[before_a])["number"],16)
    before=state_at(node_a,before_a,from_key,to_key,transport)
    if before!=state_at(node_b,before_b,from_key,to_key,transport):
        raise SignedTransferFailure("Peers disagree on baseline balances/nonce/issuance")
    h=hash32(transport(node_a,"author_submitExtrinsic",[sender_ext]),
             "submit extrinsic RPC hash")
    expected="0x"+blake2b(bytes.fromhex(sender_ext[2:]),digest_size=32).hexdigest()
    if h!=expected:
        raise SignedTransferFailure("Node reported a different hash from submitted signed bytes")
    found=finalized_inclusion(node_a,node_b,trusted_genesis,h,before_height,
                              time.monotonic()+timeout,transport)
    after_a=state_at(node_a,found["block_hash"],from_key,to_key,transport)
    after_b=state_at(node_b,found["block_hash"],from_key,to_key,transport)
    if after_a!=after_b:
        raise SignedTransferFailure("Two finalized peers disagree on balances/nonce/issuance")
    checks=check_transition(before,after_a,amount_units)
    try:
        replay=transport(node_b,"author_submitExtrinsic",[sender_ext])
    except (RuntimeError,ValueError) as exc:
        rejection=str(exc)
    else:
        raise SignedTransferFailure("Already finalized signed extrinsic replay was accepted: "+str(replay))
    return {"schema":"dvn-dev-only-two-node-real-signed-transfer-v1",
            "scope":"TESTNET_ONLY_NEVER_PRODUCTION_OR_ACTIVE_ZK_V2",
            "from_account_public":from_ss58,"to_account_public":to_ss58,
            "trusted_genesis":hash32(trusted_genesis),
            "tx_finality":found,"state_transition":checks,
            "stale_signed_extrinsic_rejected":bool(rejection),
            "active_private_zk_settlement_verified":False,
            "public_wallet_signer_verified":False,
            "physical_gpu_mining_verified":False,
            "mainnet_ready":False}

def main():
    p=argparse.ArgumentParser(description="Probe a REAL pre-signed DEV extrinsic; no secrets accepted")
    p.add_argument("--node-a",default="http://127.0.0.1:19541")
    p.add_argument("--node-b",default="http://127.0.0.1:19542")
    p.add_argument("--trusted-genesis",required=True)
    p.add_argument("--from-public",required=True)
    p.add_argument("--to-public",required=True)
    p.add_argument("--amount-units",required=True,type=int)
    p.add_argument("--signed-extrinsic-file",required=True,type=Path,
                   help="Full signed SCALE extrinsic hex only. NEVER mnemonic, seed, private key.")
    p.add_argument("--timeout",default=120,type=int)
    p.add_argument("--json-out",required=True,type=Path)
    a=p.parse_args()
    ext=a.signed_extrinsic_file.read_text(encoding="utf-8")
    result=accept_dev_transfer(node_a=a.node_a,node_b=a.node_b,
        trusted_genesis=a.trusted_genesis,from_ss58=a.from_public,
        to_ss58=a.to_public,amount_units=a.amount_units,
        signed_hex=ext,timeout=a.timeout)
    a.json_out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("REAL finalized native transfer verified against both DEV nodes, nonce, fees, supply and replay")
if __name__=="__main__":
    main()
