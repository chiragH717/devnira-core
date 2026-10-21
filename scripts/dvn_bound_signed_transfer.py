#!/usr/bin/env python3
"""Link an OFFLINE DEV-only signed blob to one previously pinned signing intent.

This binding is *not* a cryptographic signature verifier; only actual runtime
acceptance and two finalized nodes establish whether a signature was valid.
Does not generate, request, print or store mnemonic/private keys.
"""
from __future__ import annotations
import argparse
from hashlib import blake2b,sha256
import json
from pathlib import Path
import re

from scripts.dvn_unsigned_dev_signing_intent import canonical,checked_metadata
from scripts.dvn_signed_transfer_acceptance import (
    accept_dev_transfer,account_key,state_at,transaction_hex,RUNTIME_SPEC,hash32,
    SignedTransferFailure,
)
from scripts.test_two_node_rpc import rpc
from wallet.network_identity import validate_local_rpc
from spec.ss58_company_account import decode_ss58_account

HEX64=re.compile(r"[0-9a-f]{64}\Z")
SIGNED_CONTEXT="QUANTUS_EXTRINSIC"
INTENT_SCHEMA="devnira-prewallet-dev-signed-transfer-intent-v1"
CLAIM_SCHEMA="devnira-offline-dev-signed-extrinsic-binding-v1"
MAX_JSON=1024*1024
MAX_EXTRINSIC=160*1024

class DevSigningBindingRejected(ValueError):pass

def unique_pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise DevSigningBindingRejected("Duplicate JSON field refused: "+key)
        result[key]=value
    return result

def load_json(path:Path)->dict:
    p=Path(path)
    if p.is_symlink() or not p.is_file() or not 0<p.stat().st_size<=MAX_JSON:
        raise DevSigningBindingRejected("Missing, symlinked or oversized public JSON")
    try:
        data=json.loads(p.read_text("utf-8"),object_pairs_hook=unique_pairs,
                        parse_constant=lambda v: (_ for _ in ()).throw(
                            DevSigningBindingRejected("Nonfinite JSON refused")))
    except DevSigningBindingRejected:
        raise
    except (UnicodeError,ValueError) as exc:
        raise DevSigningBindingRejected("Invalid canonical public JSON") from exc
    if not isinstance(data,dict):raise DevSigningBindingRejected("JSON object required")
    forbidden=("seed","secret","mnemonic","private","password","recovery")
    def scan(v):
        if isinstance(v,dict):
            for key,child in v.items():
                if any(tag in key.lower() for tag in forbidden):
                    raise DevSigningBindingRejected("Wallet SECRET field detected; refuse to handle")
                scan(child)
        elif isinstance(v,list):
            for child in v:scan(child)
    scan(data)
    return data

EXPECTED_INTENT={
    "schema","kind","chain_genesis","runtime","spec_version",
    "transaction_version","runtime_metadata_blake2b256",
    "finalized_anchor_hash","finalized_anchor_height","expires_after_height",
    "sender_ss58_190","recipient_ss58_190","nonce",
    "amount_base_units","max_fee_base_units","chain_id_test_only",
    "contains_signed_payload","secret_material","production_send_authorized",
}

def validate_intent(document:dict)->dict:
    if not isinstance(document,dict) or set(document)!={
        "intent","intent_sha256","signer_requirements","signed_extrinsic","mainnet_ready"
    }:
        raise DevSigningBindingRejected("Unexpected unsigned intent document")
    item=document["intent"]
    if not isinstance(item,dict) or set(item)!=EXPECTED_INTENT:
        raise DevSigningBindingRejected("Unsigned intent fields unexpectedly changed")
    if (item["schema"]!=INTENT_SCHEMA or item["kind"]!="UNSIGNED_NONCUSTODIAL_DEV_TEST_ONLY"
        or item["runtime"]!=RUNTIME_SPEC or item["chain_id_test_only"] is not True
        or item["contains_signed_payload"] is not False
        or item["secret_material"] is not False
        or item["production_send_authorized"] is not False
        or document["mainnet_ready"] is not False
        or document["signed_extrinsic"] is not None):
        raise DevSigningBindingRejected("Intent is not an unsigned isolated DEV request")
    if not isinstance(document["signer_requirements"],list):
        raise DevSigningBindingRejected("DEV external signer requirements absent")
    expected=sha256(canonical(item)).hexdigest()
    if document["intent_sha256"]!=expected:
        raise DevSigningBindingRejected("Signed intent source has been changed since approval")
    for key in ("chain_genesis","finalized_anchor_hash"):
        hash32(item[key],key)
    if item["chain_genesis"]=="0x"+"0"*64:
        raise DevSigningBindingRejected("All-zero chain genesis refused")
    if (not isinstance(item["runtime_metadata_blake2b256"],str)
        or not re.fullmatch(r"0x[0-9a-f]{64}",item["runtime_metadata_blake2b256"])):
        raise DevSigningBindingRejected("Missing canonical DEV runtime metadata hash")
    try:
        sender=decode_ss58_account(item["sender_ss58_190"],190)
        recipient=decode_ss58_account(item["recipient_ss58_190"],190)
    except ValueError as exc:
        raise DevSigningBindingRejected("Invalid public SS58-190 addresses") from exc
    if sender==recipient:raise DevSigningBindingRejected("Self transfer intent forbidden")
    numeric=("spec_version","transaction_version","finalized_anchor_height",
             "expires_after_height","nonce","amount_base_units","max_fee_base_units")
    if any(type(item[k]) is not int for k in numeric):
        raise DevSigningBindingRejected("DEV intent uses noninteger chain values")
    anchor=item["finalized_anchor_height"]
    if (anchor<1 or item["expires_after_height"]<=anchor
        or item["expires_after_height"]-anchor>64
        or item["spec_version"]<1 or item["transaction_version"]<1
        or not 0<=item["nonce"]<2**32
        or not 0<item["amount_base_units"]<=10**16
        or not 0<item["max_fee_base_units"]<=10**13):
        raise DevSigningBindingRejected("Unsigned transfer era/nonce/fees/amount invalid")
    return item

def validate_claim(claim:dict,item:dict,intent_digest:str,signed_hex:str)->str:
    if not isinstance(claim,dict) or set(claim)!={
        "schema","intent_sha256","signed_extrinsic_blake2b256",
        "sender_ss58_190","signing_context","runtime"
    }:
        raise DevSigningBindingRejected("Expected only public signer linkage fields")
    if claim["schema"]!=CLAIM_SCHEMA or claim["signing_context"]!=SIGNED_CONTEXT:
        raise DevSigningBindingRejected("Wrong native FIPS-204 extrinsic signing context")
    if (claim["intent_sha256"]!=intent_digest or
        claim["sender_ss58_190"]!=item["sender_ss58_190"] or
        claim["runtime"]!=RUNTIME_SPEC):
        raise DevSigningBindingRejected("Signed bytes were not linked to this DEV signing intent")
    tx_hash="0x"+blake2b(bytes.fromhex(signed_hex[2:]),digest_size=32).hexdigest()
    if claim["signed_extrinsic_blake2b256"]!=tx_hash:
        raise DevSigningBindingRejected("Offline signed extrinsic digest mismatch")
    return tx_hash

def observe_before(url:str,item:dict,transport=rpc)->dict:
    validate_local_rpc(url)
    genesis=hash32(transport(url,"chain_getBlockHash",[0]),"DEV genesis")
    if genesis!=item["chain_genesis"]:
        raise DevSigningBindingRejected("Cross-chain replay: wrong DEV genesis")
    head=hash32(transport(url,"chain_getFinalizedHead"),"finalized head")
    header=transport(url,"chain_getHeader",[head])
    if not isinstance(header,dict) or not isinstance(header.get("number"),str):
        raise DevSigningBindingRejected("Missing canonical finalized DEV header")
    try:height=int(header["number"],16)
    except (ValueError,TypeError) as exc:
        raise DevSigningBindingRejected("Invalid finalized block number") from exc
    if not item["finalized_anchor_height"]<=height<=item["expires_after_height"]:
        raise DevSigningBindingRejected("Signed test intent expired/not yet anchored")
    if hash32(transport(url,"chain_getBlockHash",[height]))!=head:
        raise DevSigningBindingRejected("Finalized head is not canonical at requested height")
    anchored=hash32(transport(url,"chain_getBlockHash",
        [item["finalized_anchor_height"]]),"anchored block")
    if anchored!=item["finalized_anchor_hash"]:
        raise DevSigningBindingRejected("Finalized anchor forked or was changed")
    version=transport(url,"state_getRuntimeVersion")
    props=transport(url,"system_properties")
    if (not isinstance(version,dict) or version.get("specName")!=RUNTIME_SPEC
        or version.get("specVersion")!=item["spec_version"]
        or version.get("transactionVersion")!=item["transaction_version"]
        or not isinstance(props,dict)
        or (props.get("tokenDecimals"),props.get("tokenSymbol"),
            props.get("ss58Format"))!=(8,"DVN",190)):
        raise DevSigningBindingRejected("Runtime changed after offline signing intent")
    if checked_metadata(transport(url,"state_getMetadata"))!=item["runtime_metadata_blake2b256"]:
        raise DevSigningBindingRejected("DEV runtime metadata changed since signing")
    key_a=account_key(item["sender_ss58_190"])
    key_b=account_key(item["recipient_ss58_190"])
    snap=state_at(url,head,key_a,key_b,transport)
    if snap["sender"]["nonce"]!=item["nonce"]:
        raise DevSigningBindingRejected("Signer nonce stale or already used")
    if (snap["sender"]["free"]-snap["sender"]["frozen"] <
        item["amount_base_units"]+item["max_fee_base_units"]):
        raise DevSigningBindingRejected("Sender no longer has amount plus maximum fee")
    peers=transport(url,"system_peers")
    if not isinstance(peers,list) or not peers:
        raise DevSigningBindingRejected("Live DEV node has no connected peer")
    return {"genesis":genesis,"head":head,"height":height,
            "runtime":version,"state":snap}

def submit_bound_signed_dev(*,intent_file:Path,signed_file:Path,claim_file:Path,
                            node_a:str,node_b:str,timeout:int=120,transport=rpc)->dict:
    if node_a==node_b:
        raise DevSigningBindingRejected("Two independent DEV peers are mandatory")
    for endpoint in (node_a,node_b):validate_local_rpc(endpoint)
    data=load_json(intent_file)
    item=validate_intent(data)
    claim=load_json(claim_file)
    p=Path(signed_file)
    if p.is_symlink() or not p.is_file() or not 0<p.stat().st_size<=MAX_EXTRINSIC:
        raise DevSigningBindingRejected("Missing, symlinked or oversized signed SCALE file")
    try:signed_hex=transaction_hex(p.read_text("ascii"))
    except (UnicodeError,ValueError) as exc:
        raise DevSigningBindingRejected("Invalid signed DEV SCALE encoding") from exc
    expected_hash=validate_claim(claim,item,data["intent_sha256"],signed_hex)
    left=observe_before(node_a,item,transport)
    right=observe_before(node_b,item,transport)
    if left!=right:
        raise DevSigningBindingRejected("Two finalized DEV nodes disagree on pre-send state")
    # Actual validity of post-quantum Dilithium signature is established ONLY
    # by real on-chain signed extrinsic verification, not by this claim JSON.
    result=accept_dev_transfer(node_a=node_a,node_b=node_b,
        trusted_genesis=item["chain_genesis"],
        from_ss58=item["sender_ss58_190"],to_ss58=item["recipient_ss58_190"],
        amount_units=item["amount_base_units"],signed_hex=signed_hex,
        timeout=timeout,transport=transport)
    if result["tx_finality"]["extrinsic_hash"]!=expected_hash:
        raise DevSigningBindingRejected("Finalized extrinsic hash differed from signer claim")
    if result["state_transition"]["nonce_before"]!=item["nonce"]:
        raise DevSigningBindingRejected("Transaction nonce was not signing intent nonce")
    if result["state_transition"]["finalized_fee_units"]>item["max_fee_base_units"]:
        raise DevSigningBindingRejected("Native finalized fee exceeded offline max fee")
    return {"schema":"dvn-dev-signed-intent-finality-binding-v1",
            "network":"ISOLATED_LOCAL_DEVELOPMENT_ONLY",
            "intent_sha256":data["intent_sha256"],
            "source_signed_extrinsic_sha":expected_hash,
            "both_peers_checked":True,"finalized_transfer":result,
            "signer_claim_is_not_cryptographic_signature_proof":True,
            "active_v2_settlement":False,"mainnet_ready":False}

def main():
    parser=argparse.ArgumentParser(description="Manual test-only signed DEV transfer; no keys")
    parser.add_argument("--intent-file",required=True,type=Path)
    parser.add_argument("--signed-file",required=True,type=Path)
    parser.add_argument("--claim-file",required=True,type=Path)
    parser.add_argument("--node-a",default="http://127.0.0.1:19541")
    parser.add_argument("--node-b",default="http://127.0.0.1:19542")
    parser.add_argument("--timeout",default=120,type=int)
    parser.add_argument("--json-out",required=True,type=Path)
    args=parser.parse_args()
    report=submit_bound_signed_dev(intent_file=args.intent_file,
        signed_file=args.signed_file,claim_file=args.claim_file,
        node_a=args.node_a,node_b=args.node_b,timeout=args.timeout)
    if args.json_out.exists() or args.json_out.is_symlink():
        parser.error("Refusing to overwrite previous signed DEV transaction evidence")
    args.json_out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("Only LOCAL DEV network confirmed finalized signed transaction. NOT mainnet.")
if __name__=="__main__":
    main()
