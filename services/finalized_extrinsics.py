"""Opaque finalized SCALE extrinsic hashes. No transaction or address decoding.

Works only with independently genesis-pinned FINALIZED blocks. Preserves repeated
unsigned extrinsic hash occurrences and migrates the v1 SQLite DB atomically.
"""
from __future__ import annotations
import hashlib
import json
import sqlite3
from pathlib import Path
from services.network_rpc import valid_hash

V2_SCHEMA = 'dvn-finalized-raw-extrinsic-index-v2'
V1_SCHEMA = 'dvn-finalized-raw-index-v1'

class ExtrinsicRejected(ValueError):
    pass

def canonical(raw: str) -> str:
    if (not isinstance(raw,str) or not raw.startswith('0x') or
            len(raw) <= 2 or len(raw)>200_000 or len(raw)%2 or
            any(c not in '0123456789abcdefABCDEF' for c in raw[2:])):
        raise ExtrinsicRejected('Malformed opaque SCALE extrinsic')
    return raw.lower()

def hash_extrinsic(raw: str) -> str:
    return '0x'+hashlib.blake2b(bytes.fromhex(canonical(raw)[2:]),digest_size=32).hexdigest()

def rows_from_block(height: int, extrinsics: list) -> list[tuple]:
    if not isinstance(extrinsics,list):
        raise ExtrinsicRejected('Extrinsic payload must be a list')
    return [(height,i,hash_extrinsic(v),canonical(v)) for i,v in enumerate(extrinsics)]

def init_or_migrate(db: sqlite3.Connection, previous: dict, genesis: str) -> None:
    # Call INSIDE the same metadata schema transaction.
    if previous and previous not in (
            {'schema':V1_SCHEMA,'genesis':genesis.lower()},
            {'schema':V2_SCHEMA,'genesis':genesis.lower()}):
        raise ExtrinsicRejected('Wrong genesis/schema for finalized raw extrinsics')
    db.execute('''CREATE TABLE IF NOT EXISTS finalized_extrinsics
        (block_height INTEGER NOT NULL, ordinal INTEGER NOT NULL CHECK(ordinal>=0),
         extrinsic_hash TEXT NOT NULL, raw_hex TEXT NOT NULL,
         PRIMARY KEY(block_height,ordinal),
         FOREIGN KEY(block_height) REFERENCES finalized_blocks(height))''')
    db.execute('''CREATE INDEX IF NOT EXISTS finalized_extrinsic_hash_lookup
        ON finalized_extrinsics(extrinsic_hash)''')
    if previous.get('schema')==V1_SCHEMA:
        if db.execute('SELECT COUNT(*) FROM finalized_extrinsics').fetchone()[0]:
            raise ExtrinsicRejected('V1 database has unexpected extrinsic rows')
        rows=[]
        for height,rawjson in db.execute('SELECT height,extrinsics_json FROM finalized_blocks ORDER BY height'):
            try: extrinsics=json.loads(rawjson)
            except (ValueError,TypeError) as exc:
                raise ExtrinsicRejected('Corrupted V1 extrinsic JSON') from exc
            rows.extend(rows_from_block(height,extrinsics))
        insert_rows(db,rows)
        db.execute("UPDATE metadata SET value=? WHERE key='schema'",(V2_SCHEMA,))

def insert_rows(db: sqlite3.Connection, rows: list[tuple]) -> None:
    db.executemany('''INSERT INTO finalized_extrinsics
        (block_height,ordinal,extrinsic_hash,raw_hex) VALUES (?,?,?,?)''',rows)

def validate_checkpoint(db: sqlite3.Connection, height: int) -> None:
    rec=db.execute('SELECT extrinsics_json FROM finalized_blocks WHERE height=?',(height,)).fetchone()
    if rec is None: raise ExtrinsicRejected('Missing finalized block checkpoint')
    try: extrinsics=json.loads(rec[0])
    except (ValueError,TypeError) as exc:
        raise ExtrinsicRejected('Damaged finalized block JSON') from exc
    expected=rows_from_block(height,extrinsics)
    actual=db.execute('''SELECT block_height,ordinal,extrinsic_hash,raw_hex
        FROM finalized_extrinsics WHERE block_height=? ORDER BY ordinal''',(height,)).fetchall()
    if expected!=actual:
        raise ExtrinsicRejected('Finalized raw extrinsic index integrity violation')

def lookup_extrinsic(db_path: Path, digest: str, *, limit: int=25) -> dict | None:
    from services.finalized_indexer import _db_connect
    if not valid_hash(digest): raise ExtrinsicRejected('Invalid 32-byte extrinsic hash')
    if type(limit) is not int or not 1<=limit<=100:
        raise ExtrinsicRejected('Invalid bounded lookup limit')
    db=_db_connect(db_path,readonly=True)
    try:
        metadata=dict(db.execute('SELECT key,value FROM metadata'))
        if metadata.get('schema')!=V2_SCHEMA or not valid_hash(metadata.get('genesis')):
            raise ExtrinsicRejected('Extrinsic index not initialized or not migrated')
        matches=db.execute('''SELECT e.block_height,e.ordinal,e.raw_hex,b.hash
            FROM finalized_extrinsics e JOIN finalized_blocks b ON b.height=e.block_height
            WHERE e.extrinsic_hash=? ORDER BY e.block_height,e.ordinal LIMIT ?''',
            (digest.lower(),limit+1)).fetchall()
        if not matches: return None
        out=[]
        for height,ordinal,raw,block_hash in matches[:limit]:
            if hash_extrinsic(raw)!=digest.lower():
                raise ExtrinsicRejected('Corrupt extrinsic hash lookup integrity violation')
            validate_checkpoint(db,height)
            out.append({'height':height,'ordinal':ordinal,'block_hash':block_hash,
                        'raw_scale_hex':raw,'finality_confirmed':True,'decoded':False})
        return {'extrinsic_hash':digest.lower(),'occurrences':out,
                'more_occurrences':len(matches)>limit,'genesis':metadata['genesis'],
                'transactions_decoded':False,'mainnet_ready':False}
    except sqlite3.DatabaseError as exc:
        raise ExtrinsicRejected('Corrupted SQLite extrinsic index') from exc
    finally: db.close()
