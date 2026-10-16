"""SQLite finalized-block indexer for the independent DEVNIRA RPC (DEV ONLY).

Indexes raw SCALE hex, never guesses decoded balances or transactions. Uses
historically immutable FINALIZED blocks and rejects any finalized reorg,
foreign genesis, parent mismatch or RPC inconsistency without rewriting data.
This does not validate PoW, author transactions or deploy a public explorer.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sqlite3
from urllib.parse import quote

from services.network_rpc import ChainRejected, GuardedRpc, NodeIdentity, valid_hash
from services.finalized_extrinsics import (V2_SCHEMA,V1_SCHEMA,canonical,hash_extrinsic,
    rows_from_block,init_or_migrate,insert_rows,validate_checkpoint,ExtrinsicRejected)

SCHEMA_VERSION = V2_SCHEMA
HEIGHT_LIMIT = 2**63 - 1

class IndexRejected(ValueError):
    pass

def _db_connect(db_path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    path = Path(db_path).expanduser().absolute()
    if path.is_symlink():
        raise IndexRejected("Database file must not be a symlink")
    if readonly:
        if not path.is_file():
            raise IndexRejected("No indexed local database exists")
        uri = "file:" + quote(str(path), safe="/") + "?mode=ro"
        con = sqlite3.connect(uri, uri=True, timeout=5)
        con.execute("PRAGMA query_only=ON")
    else:
        if not path.parent.is_dir():
            raise IndexRejected("Database parent directory must exist")
        con = sqlite3.connect(str(path), timeout=5)
        con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA trusted_schema=OFF")
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA busy_timeout=5000")
    return con

def _create_schema(db: sqlite3.Connection, genesis: str):
    with db:
        db.execute("""CREATE TABLE IF NOT EXISTS metadata
            (key TEXT PRIMARY KEY, value TEXT NOT NULL)""")
        db.execute("""CREATE TABLE IF NOT EXISTS finalized_blocks
            (height INTEGER PRIMARY KEY CHECK(height >= 0),
             hash TEXT NOT NULL UNIQUE, parent_hash TEXT NOT NULL,
             extrinsics_json TEXT NOT NULL)""")
        previous = dict(db.execute("SELECT key, value FROM metadata"))
        if previous:
            if previous not in ({"schema":SCHEMA_VERSION, "genesis":genesis.lower()},
                                {"schema":V1_SCHEMA, "genesis":genesis.lower()}):
                raise IndexRejected("Database belongs to a foreign genesis/schema")
        else:
            if db.execute("SELECT COUNT(*) FROM finalized_blocks").fetchone()[0]:
                raise IndexRejected("Unattributed previously indexed rows detected")
            db.executemany("INSERT INTO metadata(key,value) VALUES (?,?)",
                           [("schema",SCHEMA_VERSION),("genesis",genesis.lower())])
        init_or_migrate(db,previous,genesis)

def _last(db):
    return db.execute("SELECT height,hash FROM finalized_blocks ORDER BY height DESC LIMIT 1").fetchone()

def _same(a, b):
    return isinstance(a,str) and isinstance(b,str) and a.lower()==b.lower()

def _chain_hash(rpc, height):
    value=rpc.call("chain_getBlockHash",[height])
    if not valid_hash(value):
        raise IndexRejected("Missing canonical finalized block hash")
    return value.lower()

def index_finalized_batch(rpc: GuardedRpc, db_path: Path, *, limit: int = 100) -> dict:
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise IndexRejected("Batch size outside bounded safe range")
    status = rpc.finalized_status()  # Calls GuardedRpc.verify_identity
    genesis = status.get("genesis_hash")
    height = status.get("finalized_height")
    head = status.get("finalized_hash")
    if not valid_hash(genesis) or not valid_hash(head) or type(height) is not int or not 0 <= height <= HEIGHT_LIMIT:
        raise IndexRejected("Malformed independent finalized-chain identity")
    if not _same(genesis, rpc.identity.genesis_hash):
        raise IndexRejected("RPC genesis differs from independently pinned chain")
    # Even if a malicious/buggy RPC reports a matching genesis in its status,
    # re-check height zero against the canonical block-hash database method.
    # A mocked client's untruthful identity must not bypass this invariant.
    if not _same(_chain_hash(rpc,0),genesis):
        raise IndexRejected("Node genesis hash changed despite reported chain identity")
    if not _same(_chain_hash(rpc,height), head):
        raise IndexRejected("Node disagrees with its own finalized head")
    db = _db_connect(db_path)
    try:
        _create_schema(db, genesis)
        last = _last(db)
        if last:
            validate_checkpoint(db,last[0])
            prior_height, prior_hash = last
            if prior_height > height or not _same(_chain_hash(rpc,prior_height), prior_hash):
                raise IndexRejected("FINALITY VIOLATION: indexed historical block changed; refuse rollback")
        start = 0 if last is None else last[0]+1
        end = min(height,start+limit-1)
        rows = []
        expected_parent = last[1] if last else None
        for number in range(start,end+1):
            expected_hash = _chain_hash(rpc,number)
            block = rpc.block_at_height(number)  # GuardedRpc pins genesis/8 decimals
            if not isinstance(block,dict) or block.get("height") != number or not _same(block.get("hash"),expected_hash):
                raise IndexRejected("Unstable block hash or height during finalized read")
            header=block.get("header")
            extrinsics=block.get("extrinsics_hex")
            if not isinstance(header,dict) or not isinstance(extrinsics,list):
                raise IndexRejected("Incomplete native block data")
            parent=header.get("parentHash")
            if not valid_hash(parent):
                raise IndexRejected("Missing or malformed parent hash")
            if expected_parent is not None and not _same(parent,expected_parent):
                raise IndexRejected("Broken finalized block parent linkage")
            canonical_raw=[canonical(v) for v in extrinsics]
            rows.append((number,expected_hash,parent.lower(),json.dumps(canonical_raw,separators=(",",":"))))
            expected_parent=expected_hash
        # Validate snapshot at the end BEFORE atomic commit.
        second = rpc.finalized_status()
        if (not _same(second.get("genesis_hash"),genesis)
                or type(second.get("finalized_height")) is not int
                or second["finalized_height"] < height):
            raise IndexRejected("Finality moved backward or chain identity switched during batch")
        if not _same(_chain_hash(rpc,height),head):
            raise IndexRejected("Initial finalized header changed before commit")
        if rows and not _same(_chain_hash(rpc,rows[-1][0]),rows[-1][1]):
            raise IndexRejected("Last block changed before atomic commit")
        # Single atomic DB transaction: never write partially checked history.
        with db:
            if _last(db)!=last:
                raise IndexRejected("Concurrent index writer changed checkpoint")
            db.executemany(
                "INSERT INTO finalized_blocks(height,hash,parent_hash,extrinsics_json) VALUES (?,?,?,?)",
                rows)
            insert_rows(db,[entry for height,_,_,rawjson in rows
                for entry in rows_from_block(height,json.loads(rawjson))])
        return {"schema":SCHEMA_VERSION,"genesis":genesis.lower(),
                "indexed_this_batch":len(rows),
                "indexed_through":rows[-1][0] if rows else (last[0] if last else None),
                "observed_finalized_height":height,
                "transactions_decoded":False,"gpu_verified":False,
                "mainnet_ready":False}
    finally:
        db.close()

def lookup_block(db_path: Path, *, height: int | None = None, block_hash: str | None = None) -> dict | None:
    if (height is None)==(block_hash is None):
        raise IndexRejected("Specify exactly one block locator")
    if height is not None and (type(height) is not int or not 0 <= height <= HEIGHT_LIMIT):
        raise IndexRejected("Block height is out of range")
    if block_hash is not None and not valid_hash(block_hash):
        raise IndexRejected("Invalid block hash")
    db = _db_connect(db_path,readonly=True)
    try:
        if height is not None:
            row=db.execute("SELECT height,hash,parent_hash,extrinsics_json FROM finalized_blocks WHERE height=?",(height,)).fetchone()
        else:
            row=db.execute("SELECT height,hash,parent_hash,extrinsics_json FROM finalized_blocks WHERE hash=?",(block_hash.lower(),)).fetchone()
        if row is None: return None
        validate_checkpoint(db,row[0])
        raw=json.loads(row[3])
        return {"height":row[0],"hash":row[1],"parent_hash":row[2],
                "extrinsics_hex":raw,"extrinsic_hashes":[hash_extrinsic(x) for x in raw],
                "finality_confirmed":True,"decoded_transactions":False,"indexed_locally":True}
    except sqlite3.DatabaseError as exc:
        raise IndexRejected("Indexed database could not be trusted") from exc
    finally:
        db.close()

def index_status(db_path: Path) -> dict:
    db=_db_connect(db_path,readonly=True)
    try:
        meta=dict(db.execute("SELECT key,value FROM metadata"))
        if meta.get("schema")!=SCHEMA_VERSION or not valid_hash(meta.get("genesis")):
            raise IndexRejected("Index schema or chain identity is untrusted")
        last=_last(db)
        if last: validate_checkpoint(db,last[0])
        return {"schema":SCHEMA_VERSION,"genesis":meta["genesis"],
                "indexed_through":last[0] if last else None,
                "index_is_live":False,"transactions_decoded":False,
                "mainnet_ready":False}
    except sqlite3.DatabaseError as exc:
        raise IndexRejected("Indexed database unavailable or damaged") from exc
    finally:
        db.close()

def main():
    ap=argparse.ArgumentParser(description="Index DVN native FINALIZED raw blocks; no private keys or Send")
    ap.add_argument("--rpc",default="http://127.0.0.1:9944")
    ap.add_argument("--trusted-genesis",required=True)
    ap.add_argument("--db",type=Path,required=True,help="Local private SQLite path, outside public webroot")
    ap.add_argument("--batch",type=int,default=100)
    args=ap.parse_args()
    report=index_finalized_batch(GuardedRpc(NodeIdentity(args.rpc,args.trusted_genesis)),args.db,limit=args.batch)
    print(json.dumps(report,sort_keys=True))
if __name__=="__main__":
    main()
