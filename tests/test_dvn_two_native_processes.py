import unittest
from scripts.dvn_two_native_processes import PeerFailure,address,check
class LocalNativeP2PTest(unittest.TestCase):
    def setUp(self):
        self.a={"genesis":"0x"+"a"*64,"peer_count":1,
                "finalized_height":0,"finalized_hash":"0x"+"a"*64}
    def test_valid(self):
        check(self.a,dict(self.a))
        self.assertIn("/tcp/31541/p2p/",address("12D3KooW"+"z"*44))
    def test_not_bidirectional(self):
        with self.assertRaisesRegex(PeerFailure,"Bidirectional"):
            check(self.a,dict(self.a,peer_count=0))
    def test_foreign_genesis(self):
        with self.assertRaisesRegex(PeerFailure,"Different development genesis"):
            check(self.a,dict(self.a,genesis="0x"+"b"*64))
    def test_forked_finality(self):
        with self.assertRaisesRegex(PeerFailure,"Different finalized"):
            check(self.a,dict(self.a,finalized_hash="0x"+"b"*64))
    def test_unsafe_peer_id(self):
        for s in ("", "../private", "foo --rpc-external"):
            with self.subTest(s=s),self.assertRaises(PeerFailure):
                address(s)
if __name__=="__main__":unittest.main()
