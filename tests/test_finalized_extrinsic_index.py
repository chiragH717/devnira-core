"""Raw finalized extrinsic hash index and backwards-compatible SQLite migrations."""
import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path
from services.finalized_indexer import index_finalized_batch,index_status,lookup_block,SCHEMA_VERSION
from services.finalized_extrinsics import lookup_extrinsic,ExtrinsicRejected,hash_extrinsic
from services.explorer_api import query
from services.network_rpc import NodeIdentity

G='0x'+'a1'*32
H=[G,'0x'+'b2'*32,'0x'+'c3'*32]
class Rpc:
    identity=NodeIdentity('http://127.0.0.1:9944',G)
    def finalized_status(self):
        return {'genesis_hash':G,'finalized_hash':H[2],'finalized_height':2}
    def call(self,name,params):
        assert name=='chain_getBlockHash'
        return H[params[0]]
    def block_at_height(self,n):
        return {'height':n,'hash':H[n],
                'header':{'number':hex(n),'parentHash':H[n-1] if n else '0x'+'00'*32},
                'extrinsics_hex':['0x1234','0xaabb']}

class FinalizedRawExtrinsicV2Tests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.db=Path(folder.name)/'finalized.sqlite'
        self.rpc=Rpc()
    def test_blake_two_256_hash_finality_and_read_only_api(self):
        self.assertEqual(index_finalized_batch(self.rpc,self.db)['indexed_through'],2)
        h=hash_extrinsic('0x1234')
        self.assertEqual(h,'0x'+hashlib.blake2b(bytes.fromhex('1234'),digest_size=32).hexdigest())
        self.assertNotEqual(h,'0x'+hashlib.sha256(bytes.fromhex('1234')).hexdigest())
        self.assertEqual(lookup_block(self.db,height=1)['extrinsic_hashes'][0],h)
        result=lookup_extrinsic(self.db,h)
        self.assertFalse(result['mainnet_ready'])
        self.assertFalse(result['transactions_decoded'])
        self.assertEqual([(x['height'],x['ordinal']) for x in result['occurrences']],[(0,0),(1,0),(2,0)])
        self.assertTrue(all(x['finality_confirmed'] for x in result['occurrences']))
        self.assertEqual(query(self.rpc,'/api/index/extrinsic/'+h,self.db)[0],200)
        self.assertEqual(query(self.rpc,'/api/index/extrinsic/'+h)[0],404)
        self.assertEqual(query(self.rpc,'/api/index/extrinsic/0x'+'00'*32,self.db)[0],404)
        self.assertTrue(lookup_extrinsic(self.db,h,limit=1)['more_occurrences'])
        self.assertFalse(lookup_extrinsic(self.db,h,limit=3)['more_occurrences'])
        for invalid in (0,101,True,2.0):
            with self.assertRaises(ExtrinsicRejected): lookup_extrinsic(self.db,h,limit=invalid)
    def test_v1_migration_preserves_original_finalized_records(self):
        index_finalized_batch(self.rpc,self.db)
        with sqlite3.connect(self.db) as db:
            original=db.execute('SELECT * FROM finalized_blocks ORDER BY height').fetchall()
            db.execute('DROP TABLE finalized_extrinsics')
            db.execute("UPDATE metadata SET value='dvn-finalized-raw-index-v1' WHERE key='schema'")
        with self.assertRaises(ExtrinsicRejected):lookup_extrinsic(self.db,hash_extrinsic('0x1234'))
        self.assertEqual(index_finalized_batch(self.rpc,self.db)['indexed_this_batch'],0)
        with sqlite3.connect(self.db) as db:
            self.assertEqual(original,db.execute('SELECT * FROM finalized_blocks ORDER BY height').fetchall())
            self.assertEqual(db.execute("SELECT value FROM metadata WHERE key='schema'").fetchone()[0],SCHEMA_VERSION)
        self.assertEqual(len(lookup_extrinsic(self.db,hash_extrinsic('0x1234'))['occurrences']),3)
    def test_reject_corrupt_v1_and_roll_back_migration(self):
        index_finalized_batch(self.rpc,self.db)
        with sqlite3.connect(self.db) as db:
            db.execute('DROP TABLE finalized_extrinsics')
            db.execute("UPDATE metadata SET value='dvn-finalized-raw-index-v1' WHERE key='schema'")
            db.execute('UPDATE finalized_blocks SET extrinsics_json=? WHERE height=1',('["bad"]',))
        with self.assertRaisesRegex(ExtrinsicRejected,'Malformed'):
            index_finalized_batch(self.rpc,self.db)
        with sqlite3.connect(self.db) as db:
            self.assertEqual(db.execute("SELECT value FROM metadata WHERE key='schema'").fetchone()[0],
                             'dvn-finalized-raw-index-v1')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM finalized_extrinsics').fetchone()[0],0)
    def test_tampered_checkpoint_refuses_lookups_and_reindex(self):
        index_finalized_batch(self.rpc,self.db)
        with sqlite3.connect(self.db) as db:
            db.execute("UPDATE finalized_extrinsics SET raw_hex='0xabcd' WHERE block_height=2 AND ordinal=0")
        with self.assertRaisesRegex(ExtrinsicRejected,'integrity'):
            lookup_block(self.db,height=2)
        with self.assertRaisesRegex(ExtrinsicRejected,'integrity'):
            lookup_extrinsic(self.db,hash_extrinsic('0x1234'))
        with self.assertRaisesRegex(ExtrinsicRejected,'integrity'):
            index_finalized_batch(self.rpc,self.db)
    def test_raw_validation_is_fail_closed(self):
        class InvalidRpc(Rpc):
            broken=None
            def block_at_height(self,n):
                result=super().block_at_height(n)
                result['extrinsics_hex']=[self.broken]
                return result
        rpc=InvalidRpc()
        for bad in ('0x','0x123','0xZZ','0X1234','0x'+'ab'*100001):
            rpc.broken=bad
            with self.subTest(bad=bad[:15]),self.assertRaises(ExtrinsicRejected):
                index_finalized_batch(rpc,self.db)
            self.assertIsNone(index_status(self.db)['indexed_through'])
    def test_incremental_replay_idempotence(self):
        index_finalized_batch(self.rpc,self.db,limit=1)
        self.assertEqual(len(lookup_extrinsic(self.db,hash_extrinsic('0xaabb'))['occurrences']),1)
        index_finalized_batch(self.rpc,self.db,limit=1)
        index_finalized_batch(self.rpc,self.db)
        self.assertEqual(index_finalized_batch(self.rpc,self.db)['indexed_this_batch'],0)
        self.assertEqual(len(lookup_extrinsic(self.db,hash_extrinsic('0xaabb'))['occurrences']),3)
if __name__=='__main__':unittest.main()
