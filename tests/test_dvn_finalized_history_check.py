"""Negative tests for full RPC historical ancestry, fork and restart integrity."""
import copy
import unittest
from scripts.dvn_finalized_history_check import (
    HistoryFailure,inspect,compare_pair,compare_restart,HEX32
)
HASH={i:"0x"+format(i,"064x") for i in range(1,15)}
GEN=HASH[1]
def fixtures(tamper=None):
    data={}
    for n in range(0,4):
        data[("chain_getBlockHash",n)]=HASH[n+1]
    for n in range(1,4):
        data[("chain_getHeader",HASH[n+1])]={
            "number":hex(n),"parentHash":HASH[n],"stateRoot":HASH[7],
            "extrinsicsRoot":HASH[8],"zkTreeRoot":HASH[n+9],
            "digest":{"logs":[]}}
    if tamper:tamper(data)
    def rpc(url,name,params=None):
        return copy.deepcopy(data[(name,params[0])])
    return rpc
class FinalizedAncestryTests(unittest.TestCase):
    def test_three_real_indexed_headers_and_genesis_parent(self):
        a=inspect("http://127.0.0.1:19541",GEN,3,transport=fixtures())
        self.assertEqual(a["oldest"],1)
        self.assertEqual(len(a["records"]),3)
        self.assertEqual(a["records"]["1"]["parent"],GEN)
        self.assertTrue(compare_pair(a,copy.deepcopy(a))["same_canonical_history"])
        self.assertTrue(compare_restart(a,copy.deepcopy(a))["historic_header_roots_preserved"])
        self.assertFalse(a["root_field_is_production_v2_activated"])
    def test_fail_on_genesis_only_or_unbounded_height(self):
        for n in (0,-1):
            with self.assertRaises(HistoryFailure):inspect("x",GEN,n,transport=fixtures())
        for depth in (0,65,-4):
            with self.assertRaises(HistoryFailure):
                inspect("x",GEN,3,depth=depth,transport=fixtures())
        with self.assertRaises(HistoryFailure):
            inspect("x","0x"+"0"*64,3,transport=fixtures())
    def test_missing_wrong_parent_fork_historic_root_and_number(self):
        cases=[
            lambda d:d[("chain_getHeader",HASH[4])].update(parentHash=HASH[6]),
            lambda d:d[("chain_getHeader",HASH[2])].update(parentHash=HASH[6]),
            lambda d:d[("chain_getHeader",HASH[3])].update(zkTreeRoot="0xabc"),
            lambda d:d[("chain_getHeader",HASH[3])].update(number="0x7"),
            lambda d:d[("chain_getBlockHash",2)]==HASH[6],
        ]
        for t in cases[:4]:
            with self.subTest(t=t),self.assertRaises(HistoryFailure):
                inspect("x",GEN,3,transport=fixtures(t))
    def test_diff_nodes_and_changed_history_after_restart_refuse(self):
        a=inspect("x",GEN,3,transport=fixtures())
        b=copy.deepcopy(a)
        b["records"]["1"]["zk_tree_root"]=HASH[4]
        with self.assertRaisesRegex(HistoryFailure,"Independent nodes disagree"):
            compare_pair(a,b)
        with self.assertRaisesRegex(HistoryFailure,"mutated"):
            compare_restart(a,b)
    def test_only_existing_post_genesis_window_no_unbounded_fetch(self):
        a=inspect("x",GEN,3,depth=2,transport=fixtures())
        self.assertEqual(a["oldest"],2)
        self.assertEqual(sorted(a["records"]),["2","3"])
if __name__=="__main__":
    unittest.main()
