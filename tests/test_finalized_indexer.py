import tempfile
import unittest
from pathlib import Path
from services.network_rpc import NodeIdentity
from services.finalized_indexer import IndexRejected,index_finalized_batch,index_status,lookup_block

G="0x"+"a1"*32
H1="0x"+"b2"*32
H2="0x"+"c3"*32
H3="0x"+"d4"*32
FOREIGN="0x"+"ee"*32

class MockRpc:
    identity=NodeIdentity("http://127.0.0.1:9944",G)
    def __init__(self,limit=2):
        self.height=limit
        self.hashes=[G,H1,H2,H3]
        self.bad_height=None
        self.mutate_on_second=False
        self.calls=0
        self.bad_parent=False
    def finalized_status(self):
        self.calls+=1
        if self.mutate_on_second and self.calls>1:
            self.hashes[2]=FOREIGN
        return {"genesis_hash":G,"finalized_height":self.height,
                "finalized_hash":self.hashes[self.height]}
    def call(self,name,params):
        if name!="chain_getBlockHash":raise AssertionError(name)
        return self.hashes[params[0]]
    def block_at_height(self,n):
        h=self.hashes[n]
        if n==self.bad_height:h=FOREIGN
        p=self.hashes[n-1] if n else "0x"+"00"*32
        if self.bad_parent and n==1:p=FOREIGN
        return {"height":n,"hash":h,"header":{"number":hex(n),"parentHash":p},
                "extrinsics_hex":["0x1234","0xaabb"]}

class SQLiteFinalizedTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.db=Path(t.name)/"blocks.sqlite"
        self.rpc=MockRpc()
    def test_full_finalized_index_and_offline_api_lookup(self):
        r=index_finalized_batch(self.rpc,self.db)
        self.assertEqual(r["indexed_this_batch"],3)
        self.assertEqual(r["indexed_through"],2)
        self.assertFalse(r["mainnet_ready"])
        s=index_status(self.db)
        self.assertEqual(s["indexed_through"],2)
        b=lookup_block(self.db,height=1)
        self.assertEqual(b["extrinsics_hex"],["0x1234","0xaabb"])
        self.assertTrue(b["finality_confirmed"])
        self.assertFalse(b["decoded_transactions"])
        self.assertEqual(lookup_block(self.db,block_hash=H1),b)
        from services.explorer_api import query
        self.assertEqual(query(self.rpc,"/api/index/block/1",self.db)[1]["hash"],H1)
        self.assertEqual(query(self.rpc,"/api/index/hash/"+H1,self.db)[0],200)
        self.assertEqual(query(self.rpc,"/api/index/status",self.db)[1]["indexed_through"],2)
        self.assertEqual(query(self.rpc,"/api/index/block/3",self.db)[0],404)
        self.assertEqual(query(self.rpc,"/api/index/block/1")[0],404)
    def test_reindex_idempotent_and_incremental(self):
        index_finalized_batch(self.rpc,self.db,limit=2)
        self.assertEqual(index_status(self.db)["indexed_through"],1)
        result=index_finalized_batch(self.rpc,self.db)
        self.assertEqual(result["indexed_this_batch"],1)
        self.assertEqual(index_finalized_batch(self.rpc,self.db)["indexed_this_batch"],0)
        self.rpc.height=3
        self.assertEqual(index_finalized_batch(self.rpc,self.db)["indexed_through"],3)
    def test_foreign_identity_refuses_db_switch(self):
        index_finalized_batch(self.rpc,self.db)
        self.rpc.identity=NodeIdentity("http://localhost:9944",FOREIGN)
        with self.assertRaisesRegex(IndexRejected,"pinned"):
            index_finalized_batch(self.rpc,self.db)
        self.rpc.identity=NodeIdentity("http://localhost:9944",G)
        self.rpc.hashes[0]=FOREIGN
        with self.assertRaises(IndexRejected):
            index_finalized_batch(self.rpc,self.db)
    def test_persisted_finality_reorg_is_hard_stop_no_rollback(self):
        index_finalized_batch(self.rpc,self.db)
        self.rpc.hashes[1]=FOREIGN
        self.rpc.hashes[2]=FOREIGN
        with self.assertRaisesRegex(IndexRejected,"FINALITY VIOLATION"):
            index_finalized_batch(self.rpc,self.db)
        self.assertEqual(lookup_block(self.db,height=1)["hash"],H1)
    def test_a_mid_batch_rpc_failure_leaves_no_partial_blocks(self):
        self.rpc.bad_height=2
        with self.assertRaisesRegex(IndexRejected,"Unstable"):
            index_finalized_batch(self.rpc,self.db)
        self.assertIsNone(index_status(self.db)["indexed_through"])
    def test_parent_mismatch_does_not_commit(self):
        self.rpc.bad_parent=True
        with self.assertRaisesRegex(IndexRejected,"parent linkage"):
            index_finalized_batch(self.rpc,self.db)
        self.assertIsNone(index_status(self.db)["indexed_through"])
    def test_finalized_hash_changed_between_read_and_commit(self):
        self.rpc.mutate_on_second=True
        with self.assertRaisesRegex(IndexRejected,"Initial finalized header changed"):
            index_finalized_batch(self.rpc,self.db)
        self.assertIsNone(index_status(self.db)["indexed_through"])
    def test_new_blocks_only_when_finalized(self):
        self.rpc.height=0
        self.assertEqual(index_finalized_batch(self.rpc,self.db)["indexed_through"],0)
        self.assertIsNone(lookup_block(self.db,height=1))
        self.rpc.height=1
        self.assertEqual(index_finalized_batch(self.rpc,self.db)["indexed_through"],1)
    def test_db_symlink_and_fake_lookup_rejected(self):
        t=self.db.parent/"alias.sqlite"
        t.symlink_to(self.db)
        with self.assertRaisesRegex(IndexRejected,"symlink"):
            index_finalized_batch(self.rpc,t)
        for invalid in (-1,True,2**64):
            with self.assertRaises(IndexRejected):
                lookup_block(self.db,height=invalid)
        with self.assertRaises(IndexRejected):
            index_finalized_batch(self.rpc,self.db,limit=0)
    def test_wrong_or_missing_database_refused(self):
        with self.assertRaisesRegex(IndexRejected,"No indexed"):
            index_status(self.db)
        with self.assertRaisesRegex(IndexRejected,"No indexed"):
            lookup_block(self.db,height=1)
if __name__=="__main__":
    unittest.main()
