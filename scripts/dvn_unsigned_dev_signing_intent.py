#!/usr/bin/env python3
"""Read-only immutable DEV signing intent, pinned to TWO actual finalized peers.

A signer consumes this JSON outside the node; this file intentionally never
creates mnemonic/keypairs, guesses SCALE call bytes or submits transactions.
The global wallet is NOT implemented. No real funds/production signing.
"""
from __future__ import annotations
import argparse
from hashlib import blake2b,sha256
import json
from pathlib import Path
import re

from scripts.test_two_node_rpc import rpc
from scripts.dvn_signed_transfer_acceptance import (
    SignedTransferFailure,hash32,account_key,state_at,RUNTIME_SPEC,
)
from wallet.network_identity import validate_local_rpc
from spec.ss58_company_account import decode_ss58_account

HEX_BYTES=re.compile(r"0x(?:[0-9a-fA-F]{2})+\Z")
MAX_METADATA_BYTES=8*1024*1024

class SigningIntentRejected(ValueError):pass

def checked_metadata(value:str)->str:
    if not isinstance(value,str) or not HEX_BYTES.fullmatch(value):
        raise SigningIntentRejected("Missing runtime SCALE metadata")
    data=bytes.fromhex(value[2:])
    if not 4<=len(data)<=MAX_METADATA_BYTES:
        raise SigningIntentRejected("Unbounded or empty runtime metadata")
    return "0x"+blake2b(data,digest_size=32).hexdigest()

def canonical(payload:dict)->bytes:
    return json.dumps(payload,sort_keys=True,separators=(",",":"),
                      ensure_ascii=True,allow_nan=False).encode("ascii")

def build_intent(*,node_a:str,node_b:str,trusted_genesis:str,
                 from_address:str,to_address:str,amount_units:int,
                 fee_limit_units:int,valid_blocks:int=32,transport=rpc)->dict:
    if node_a==node_b:
        raise SigningIntentRejected("Two distinct DEV endpoints required")
    for endpoint in (node_a,node_b):
        validate_local_rpc(endpoint)
    if from_address==to_address:
        raise SigningIntentRejected("Distinct sender and receiver required")
    try:
        sender=decode_ss58_account(from_address,190)
        receiver=decode_ss58_account(to_address,190)
        if sender==receiver:
            raise SigningIntentRejected("Two addresses resolve to same account")
    except ValueError as exc:
        raise SigningIntentRejected("Invalid SS58-190 public account") from exc
    if type(amount_units) is not int or not 0<amount_units<=10_000_000_000_000_000:
        raise SigningIntentRejected("Exact positive integer DVN base units required")
    if type(fee_limit_units) is not int or not 0<fee_limit_units<=10_000_000_000_000:
        raise SigningIntentRejected("Positive bounded max fee in base units required")
    if type(valid_blocks) is not int or not 1<=valid_blocks<=64:
        raise SigningIntentRejected("Bounded DEV signing era 1..64 blocks required")
    genesis=hash32(trusted_genesis,"independently approved DEV genesis")
    if genesis=="0x"+"0"*64:
        raise SigningIntentRejected("Zero genesis forbidden")
    observations=[]
    from_key,to_key=account_key(from_address),account_key(to_address)
    for url in (node_a,node_b):
        head=hash32(transport(url,"chain_getFinalizedHead"),"finalized head")
        header=transport(url,"chain_getHeader",[head])
        if not isinstance(header,dict):
            raise SigningIntentRejected("No authentic RPC finalized header")
        try: height=int(header.get("number"),16)
        except (TypeError,ValueError) as exc:
            raise SigningIntentRejected("Malformed finalized height") from exc
        if height<1 or transport(url,"chain_getBlockHash",[height])!=head:
            raise SigningIntentRejected("No canonical finalized post-genesis height")
        if hash32(transport(url,"chain_getBlockHash",[0]),"genesis")!=genesis:
            raise SigningIntentRejected("DEV genesis mismatch; no cross-chain signing")
        version=transport(url,"state_getRuntimeVersion")
        props=transport(url,"system_properties")
        if (not isinstance(version,dict) or version.get("specName")!=RUNTIME_SPEC
            or type(version.get("specVersion")) is not int
            or type(version.get("transactionVersion")) is not int
            or not isinstance(props,dict)
            or (props.get("tokenDecimals"),props.get("tokenSymbol"),
                props.get("ss58Format"))!=(8,"DVN",190)):
            raise SigningIntentRejected("Wrong 8-decimal DEV runtime or signed payload versions")
        peers=transport(url,"system_peers")
        if not isinstance(peers,list) or not peers:
            raise SigningIntentRejected("Both real nodes must have connected peers")
        metadata_hash=checked_metadata(transport(url,"state_getMetadata"))
        state=state_at(url,head,from_key,to_key,transport)
        observations.append({"head":head,"height":height,
            "spec_version":version["specVersion"],
            "transaction_version":version["transactionVersion"],
            "metadata_hash_blake2b256":metadata_hash,"state":state})
    a,b=observations
    if a!=b:
        raise SigningIntentRejected("Two finalized nodes disagree on head, metadata, nonce or balances")
    balance=a["state"]["sender"]
    if balance["free"]-balance["frozen"]<amount_units+fee_limit_units:
        raise SigningIntentRejected("Sender DEV balance cannot cover transfer plus worst-case fee")
    if balance["nonce"]<0 or balance["nonce"]>2**32-1:
        raise SigningIntentRejected("Invalid SCALE u32 transaction nonce")
    item={"schema":"devnira-prewallet-dev-signed-transfer-intent-v1",
          "kind":"UNSIGNED_NONCUSTODIAL_DEV_TEST_ONLY",
          "chain_genesis":genesis,"runtime":RUNTIME_SPEC,
          "spec_version":a["spec_version"],
          "transaction_version":a["transaction_version"],
          "runtime_metadata_blake2b256":a["metadata_hash_blake2b256"],
          "finalized_anchor_hash":a["head"],
          "finalized_anchor_height":a["height"],
          "expires_after_height":a["height"]+valid_blocks,
          "sender_ss58_190":from_address,"recipient_ss58_190":to_address,
          "nonce":balance["nonce"],
          "amount_base_units":amount_units,"max_fee_base_units":fee_limit_units,
          "chain_id_test_only":True,
          "contains_signed_payload":False,"secret_material":False,
          "production_send_authorized":False}
    digest=sha256(canonical(item)).hexdigest()
    return {"intent":item,"intent_sha256":digest,
            "signer_requirements":[
              "Derive and validate exact same DEV SS58-190 signing public key",
              "Re-read pinned DEV metadata and compare hash immediately before signing",
              "Build runtime-specific call using actual signed-extension metadata, not guessed bytes",
              "Set mortal era anchored to finalized header and require nonce+fee bound",
              "Sign with test-only Dilithium key on offline/isolated machine",
              "Pass only public fully signed SCALE extrinsic to independent acceptance tool"],
            "signed_extrinsic":None,"mainnet_ready":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--node-a",default="http://127.0.0.1:19541")
    p.add_argument("--node-b",default="http://127.0.0.1:19542")
    p.add_argument("--trusted-genesis",required=True)
    p.add_argument("--from-public",required=True)
    p.add_argument("--to-public",required=True)
    p.add_argument("--amount-units",type=int,required=True)
    p.add_argument("--max-fee-units",type=int,required=True)
    p.add_argument("--valid-blocks",type=int,default=32)
    p.add_argument("--json-out",required=True,type=Path)
    x=p.parse_args()
    data=build_intent(node_a=x.node_a,node_b=x.node_b,
       trusted_genesis=x.trusted_genesis,from_address=x.from_public,
       to_address=x.to_public,amount_units=x.amount_units,
       fee_limit_units=x.max_fee_units,valid_blocks=x.valid_blocks)
    if x.json_out.exists() or x.json_out.is_symlink():
        p.exit(2,"STOP: refusing to overwrite an existing signing intent\n")
    x.json_out.write_text(json.dumps(data,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("UNSIGNED DEV intent staged; NO private keys, signatures or production authorization")
if __name__=="__main__":main()
