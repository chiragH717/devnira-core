"""Simulated RPC fixtures, never real Dilithium signatures or transfer evidence."""
import hashlib
import unittest
from spec.ss58_company_account import encode_ss58_account
from scripts.dvn_signed_transfer_acceptance import (SignedTransferFailure,
    account_key,read_account,read_issuance,check_transition,transaction_hex,
    accept_dev_transfer)
SENDER=encode_ss58_account(bytes([7])*32)
RECIPIENT=encode_ss58_account(bytes([8])*32)
GEN="0x"+"1"*64
BEFORE="0x"+"2"*64
AFTER="0x"+"3"*64
EXTRINSIC="0x148401020304" # SYNTHETIC ONLY: not cryptographically valid
TXHASH="0x"+hashlib.blake2b(bytes.fromhex(EXTRINSIC[2:]),digest_size=32).hexdigest()
def acc(nonce,free):
    return "0x"+(nonce.to_bytes(4,"little")+(0).to_bytes(4,"little")+
        (1).to_bytes(4,"little")+(0).to_bytes(4,"little")+
        free.to_bytes(16,"little")+(0).to_bytes(16,"little")+
        (0).to_bytes(16,"little")+(1<<127).to_bytes(16,"little")).hex()
def account(n,f):
    return {"nonce":n,"free":f,"reserved":0,"frozen":0,"flags":1<<127}
class SyntheticRPC:
    def __init__(self):
        self.tips=0;self.submits=0
        self.states={(account_key(SENDER),BEFORE):acc(0,1000),
                     (account_key(RECIPIENT),BEFORE):acc(0,200),
                     (account_key(SENDER),AFTER):acc(1,880),
                     (account_key(RECIPIENT),AFTER):acc(0,300)}
    def __call__(self,url,method,params=None):
        if method=="state_getRuntimeVersion":return {"specName":"devnira-8dec-native-dev-test-runtime"}
        if method=="system_properties":return {"tokenDecimals":8,"tokenSymbol":"DVN","ss58Format":190}
        if method=="system_peers":return [{"peerId":"TEST_ONLY"}]
        if method=="chain_getBlockHash":return GEN if params==[0] else AFTER
        if method=="chain_getFinalizedHead":
            self.tips+=1;return BEFORE if self.tips<=2 else AFTER
        if method=="chain_getHeader":return {"number":"0x2" if params==[BEFORE] else "0x3"}
        if method=="state_getStorage":
            key,block=params
            if key.startswith("0xc2261276"):return "0x"+(100000).to_bytes(16,"little").hex()
            return self.states[(key,block)]
        if method=="author_submitExtrinsic":
            self.submits+=1
            if self.submits>1:raise RuntimeError("Stale nonce")
            return TXHASH
        if method=="chain_getBlock":return {"block":{"extrinsics":[EXTRINSIC]}}
        raise RuntimeError("Unexpected RPC "+method)
class SignedTransferUnitTests(unittest.TestCase):
    def test_ss58_storage_and_account_codec(self):
        key=account_key(SENDER)
        self.assertTrue(key.startswith("0x26aa394eea5630e07c48ae0c9558cef7b99d880ec681799c0cf30e8886371da9"))
        self.assertEqual(len(bytes.fromhex(key[2:])),80)
        self.assertEqual(read_account(acc(14,123))["free"],123)
        self.assertEqual(read_account(acc(14,123))["nonce"],14)
        self.assertEqual(read_issuance("0x"+(42).to_bytes(16,"little").hex()),42)
    def test_reject_unsigned_length_forged_ss58_and_broken_scale(self):
        self.assertEqual(transaction_hex(EXTRINSIC),EXTRINSIC)
        for bad in ("0x140401020304","0x108401020304","0x1484010203","0xdeadbeef","SEED WORDS"):
            with self.subTest(value=bad),self.assertRaises(SignedTransferFailure):
                transaction_hex(bad)
        with self.assertRaises(ValueError):
            account_key(encode_ss58_account(bytes([7])*32,189))
    def test_exact_balance_nonce_fee_supply_conservation(self):
        before={"sender":account(0,1000),"recipient":account(0,200),"issuance":100000}
        after={"sender":account(1,880),"recipient":account(0,300),"issuance":100000}
        self.assertEqual(check_transition(before,after,100)["finalized_fee_units"],20)
        for change in ({"sender":account(0,880)},{"sender":account(1,901)},
                       {"recipient":account(0,301)},{"recipient":account(1,300)},
                       {"issuance":100001}):
            with self.subTest(change=change),self.assertRaises(SignedTransferFailure):
                check_transition(before,{**after,**change},100)
    def test_synthetic_dev_rpc_flow_is_not_mainnet_proof(self):
        fake=SyntheticRPC()
        report=accept_dev_transfer(node_a="http://127.0.0.1:19541",
            node_b="http://127.0.0.1:19542",trusted_genesis=GEN,
            from_ss58=SENDER,to_ss58=RECIPIENT,amount_units=100,
            signed_hex=EXTRINSIC,transport=fake)
        self.assertEqual(report["state_transition"]["finalized_fee_units"],20)
        self.assertTrue(report["stale_signed_extrinsic_rejected"])
        self.assertFalse(report["mainnet_ready"])
        self.assertFalse(report["active_private_zk_settlement_verified"])
        self.assertEqual(fake.submits,2)
    def test_accepted_replay_fails_even_when_balances_seem_correct(self):
        class ReplayRPC(SyntheticRPC):
            def __call__(self,url,method,params=None):
                if method=="author_submitExtrinsic" and self.submits>=1:
                    self.submits+=1
                    return TXHASH
                return super().__call__(url,method,params)
        with self.assertRaisesRegex(SignedTransferFailure,"replay"):
            accept_dev_transfer(node_a="http://127.0.0.1:19541",
                node_b="http://127.0.0.1:19542",trusted_genesis=GEN,
                from_ss58=SENDER,to_ss58=RECIPIENT,amount_units=100,
                signed_hex=EXTRINSIC,transport=ReplayRPC())
    def test_missing_two_peers_or_foreign_endpoint_blocks_submission(self):
        for a,b in (("http://127.0.0.1:19541","http://127.0.0.1:19541"),
                    ("https://example.com","http://127.0.0.1:19542")):
            with self.subTest(url=a),self.assertRaises((SignedTransferFailure,ValueError)):
                accept_dev_transfer(node_a=a,node_b=b,trusted_genesis=GEN,
                    from_ss58=SENDER,to_ss58=RECIPIENT,amount_units=100,
                    signed_hex=EXTRINSIC,transport=SyntheticRPC())
if __name__=="__main__":
    unittest.main()
