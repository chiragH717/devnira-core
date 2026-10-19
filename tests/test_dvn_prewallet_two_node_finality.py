"""Pure security checks for actual finalized DEV headers and node identity."""
import copy
import unittest
from unittest.mock import patch
from scripts.dvn_prewallet_two_node_finality import DEV_SPEC,PeerFailure,assess_pair,checked_header,identity
HASH="0x"+"a"*64
OTHER="0x"+"b"*64
ZERO="0x"+"0"*64
GENESIS="0x"+"e"*64
HEADER={"number":"0x2","parentHash":HASH,"stateRoot":OTHER,"extrinsicsRoot":HASH,
        "zkTreeRoot":OTHER,"digest":{"logs":[]}}
def sample(n=2):return {"genesis":GENESIS,"peer_count":1,"finalized_height":n,"finalized_hash":HASH}
class LiveDevelopmentFinalityTests(unittest.TestCase):
    def test_real_matching_post_genesis_header(self):
        result=assess_pair(sample(),sample(),HASH,HASH,HEADER,HEADER)
        self.assertEqual(result["height"],2)
        self.assertEqual(result["zk_root"],OTHER)
    def test_genesis_only_never_finality(self):
        with self.assertRaisesRegex(PeerFailure,"post-genesis"):
            assess_pair(sample(0),sample(0),HASH,HASH,HEADER,HEADER)
    def test_genesis_peers_fork_hash_rejection(self):
        cases=[
            (sample(),dict(sample(),genesis=OTHER),HASH,HASH,HEADER,HEADER),
            (sample(),dict(sample(),peer_count=0),HASH,HASH,HEADER,HEADER),
            (sample(),sample(),HASH,OTHER,HEADER,HEADER),
            (sample(),dict(sample(),finalized_hash=OTHER),HASH,HASH,HEADER,HEADER),
        ]
        for case in cases:
            with self.subTest(case=case),self.assertRaises(PeerFailure):
                assess_pair(*case)
    def test_header_tamper_reject(self):
        for field,spoof in (("zkTreeRoot",HASH),("stateRoot",HASH),
                            ("number","0x3"),("digest",None),("extrinsicsRoot","0x12")):
            other=copy.deepcopy(HEADER)
            other[field]=spoof
            with self.subTest(field=field),self.assertRaises(PeerFailure):
                assess_pair(sample(),sample(),HASH,HASH,HEADER,other)
    def test_wrong_runtime_or_decimal_identity_rejected(self):
        version={"specName":DEV_SPEC}
        props={"tokenDecimals":8,"tokenSymbol":"DVN","ss58Format":190}
        d={"system_chain":"DEVNIRA Local","state_getRuntimeVersion":version,
           "chain_getBlockHash":GENESIS,"system_properties":props}
        def fake(url,method,params=None):return d[method]
        with patch("scripts.dvn_prewallet_two_node_finality.rpc",side_effect=fake):
            self.assertEqual(identity("http://127.0.0.1:19541"),GENESIS)
            d["state_getRuntimeVersion"]={"specName":"quantus-runtime"}
            with self.assertRaises(ValueError):identity("http://127.0.0.1:19541")
            d["state_getRuntimeVersion"]=version
            for key,bad in (("tokenDecimals",12),("tokenSymbol","QTC"),("ss58Format",42)):
                prior=props[key]
                props[key]=bad
                with self.subTest(key=key),self.assertRaisesRegex(PeerFailure,"Wrong token"):
                    identity("http://127.0.0.1:19541")
                props[key]=prior
    def test_malformed_header_or_zero_genesis_rejected(self):
        with self.assertRaisesRegex(PeerFailure,"invalid development genesis"):
            assess_pair(dict(sample(),genesis=ZERO),dict(sample(),genesis=ZERO),
                        HASH,HASH,HEADER,HEADER)
        for hdr in (None,{},{"number":"0x2"},dict(HEADER,zkTreeRoot="0x123")):
            with self.subTest(hdr=hdr),self.assertRaises(PeerFailure):
                checked_header(hdr,2)
if __name__=="__main__":unittest.main()
