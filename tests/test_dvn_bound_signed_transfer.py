"""DEFERRED tests for MANUAL final run. No real keys, signatures or funds here."""
import json
import tempfile
import unittest
from hashlib import blake2b,sha256
from pathlib import Path

from spec.ss58_company_account import encode_ss58_account
from scripts.dvn_unsigned_dev_signing_intent import canonical
from scripts.dvn_bound_signed_transfer import (
    CLAIM_SCHEMA,INTENT_SCHEMA,RUNTIME_SPEC,DevSigningBindingRejected,
    SIGNED_CONTEXT,load_json,validate_claim,validate_intent,observe_before
)

GENESIS="0x"+"1"*64
HEAD="0x"+"2"*64
SENDER=encode_ss58_account(bytes([7])*32,190)
RECIPIENT=encode_ss58_account(bytes([8])*32,190)
SIGNED="0x148401020304"  # fake signed-flag SCALE, NOT a real ML-DSA signature

def public_doc():
    item={
        "schema":INTENT_SCHEMA,"kind":"UNSIGNED_NONCUSTODIAL_DEV_TEST_ONLY",
        "chain_genesis":GENESIS,"runtime":RUNTIME_SPEC,
        "spec_version":153,"transaction_version":6,
        "runtime_metadata_blake2b256":"0x"+blake2b(b"meta",digest_size=32).hexdigest(),
        "finalized_anchor_hash":HEAD,"finalized_anchor_height":2,
        "expires_after_height":34,"sender_ss58_190":SENDER,
        "recipient_ss58_190":RECIPIENT,"nonce":5,
        "amount_base_units":100,"max_fee_base_units":25,
        "chain_id_test_only":True,"contains_signed_payload":False,
        "secret_material":False,"production_send_authorized":False}
    return {"intent":item,"intent_sha256":sha256(canonical(item)).hexdigest(),
            "signer_requirements":[],"signed_extrinsic":None,"mainnet_ready":False}

def signer_claim(doc):
    return {"schema":CLAIM_SCHEMA,"intent_sha256":doc["intent_sha256"],
            "signed_extrinsic_blake2b256":"0x"+blake2b(bytes.fromhex(SIGNED[2:]),
                digest_size=32).hexdigest(),
            "sender_ss58_190":SENDER,"signing_context":SIGNED_CONTEXT,
            "runtime":RUNTIME_SPEC}

def acct(nonce:int,free:int)->str:
    return "0x"+(nonce.to_bytes(4,"little")+
        (0).to_bytes(4,"little")+(1).to_bytes(4,"little")+
        (0).to_bytes(4,"little")+free.to_bytes(16,"little")+
        (0).to_bytes(16,"little")+(0).to_bytes(16,"little")+
        (1<<127).to_bytes(16,"little")).hex()

def stub_runtime(url,method,params=None):
    from scripts.dvn_signed_transfer_acceptance import account_key,TOTAL_ISSUANCE_KEY
    if method=="chain_getBlockHash":return GENESIS if params==[0] else HEAD
    if method=="chain_getFinalizedHead":return HEAD
    if method=="chain_getHeader":return {"number":"0x3"}
    if method=="state_getRuntimeVersion":
        return {"specName":RUNTIME_SPEC,"specVersion":153,"transactionVersion":6}
    if method=="system_properties":
        return {"tokenDecimals":8,"tokenSymbol":"DVN","ss58Format":190}
    if method=="state_getMetadata":return "0x"+b"meta".hex()
    if method=="system_peers":return [{"peerId":"DEV_ONLY"}]
    if method=="state_getStorage":
        key,block=params
        if key==TOTAL_ISSUANCE_KEY:
            return "0x"+(10**9).to_bytes(16,"little").hex()
        if key==account_key(SENDER):return acct(5,1000)
        if key==account_key(RECIPIENT):return acct(0,200)
    raise AssertionError((method,params))

class BoundOfflineSignerIntentionTests(unittest.TestCase):
    def test_one_intent_only_with_valid_immutable_checksum(self):
        doc=public_doc()
        self.assertEqual(validate_intent(doc)["nonce"],5)
        doc["intent"]["amount_base_units"]=200
        with self.assertRaisesRegex(DevSigningBindingRejected,"changed"):
            validate_intent(doc)

    def test_claim_bound_to_intent_blob_dilithium_context_and_public_sender(self):
        doc=public_doc()
        claim=signer_claim(doc)
        self.assertEqual(validate_claim(claim,doc["intent"],doc["intent_sha256"],SIGNED),
                         claim["signed_extrinsic_blake2b256"])
        for key,value in (("signing_context","WRONG_CONTEXT"),
                          ("intent_sha256","f"*64),
                          ("sender_ss58_190",RECIPIENT),
                          ("signed_extrinsic_blake2b256","0x"+"0"*64)):
            changed={**claim,key:value}
            with self.subTest(key=key),self.assertRaises(DevSigningBindingRejected):
                validate_claim(changed,doc["intent"],doc["intent_sha256"],SIGNED)

    def test_expired_era_nonce_and_chain_mismatch_refused(self):
        doc=public_doc()
        base=observe_before("http://127.0.0.1:19541",doc["intent"],stub_runtime)
        self.assertEqual(base["state"]["sender"]["nonce"],5)
        doc["intent"]["expires_after_height"]=2
        def future(u,m,p=None):
            return {"number":"0x23"} if m=="chain_getHeader" else stub_runtime(u,m,p)
        with self.assertRaisesRegex(DevSigningBindingRejected,"expired"):
            observe_before("http://127.0.0.1:19541",doc["intent"],future)
        def foreign(u,m,p=None):
            return "0x"+"9"*64 if m=="chain_getBlockHash" and p==[0] else stub_runtime(u,m,p)
        with self.assertRaisesRegex(DevSigningBindingRejected,"genesis"):
            observe_before("http://127.0.0.1:19541",doc["intent"],foreign)
        def nonce_drift(u,m,p=None):
            from scripts.dvn_signed_transfer_acceptance import account_key
            return acct(6,1000) if m=="state_getStorage" and p[0]==account_key(SENDER) \
                else stub_runtime(u,m,p)
        with self.assertRaisesRegex(DevSigningBindingRejected,"nonce"):
            observe_before("http://127.0.0.1:19541",public_doc()["intent"],nonce_drift)

    def test_no_plaintext_secret_keys_or_duplicate_json_fields_in_signer_claim(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"claim.json"
            p.write_text('{"schema":"a","schema":"b"}',encoding="utf-8")
            with self.assertRaisesRegex(DevSigningBindingRejected,"Duplicate JSON"):
                load_json(p)
            p.write_text('{"private_key":"NEVER"}',encoding="utf-8")
            with self.assertRaisesRegex(DevSigningBindingRejected,"SECRET"):
                load_json(p)
            p.write_text(json.dumps(signer_claim(public_doc())),encoding="utf-8")
            self.assertEqual(load_json(p)["schema"],CLAIM_SCHEMA)

    def test_refuse_unsigned_fabrication_as_ready_signed_intent(self):
        doc=public_doc()
        for key,value in (("mainnet_ready",True),("signed_extrinsic",SIGNED)):
            edited={**doc,key:value}
            with self.subTest(key=key),self.assertRaises(DevSigningBindingRejected):
                validate_intent(edited)
        doc["intent"]["chain_genesis"]="0x"+"0"*64
        doc["intent_sha256"]=sha256(canonical(doc["intent"])).hexdigest()
        with self.assertRaisesRegex(DevSigningBindingRejected,"zero"):
            validate_intent(doc)

if __name__=="__main__":
    unittest.main()
