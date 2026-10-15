# DEVNIRA finalized-block SQLite explorer indexer — local development

PR #18 implements a durable local **raw finalized-block** indexer, not just
the previous transient HTTP proxy. It stores a nonzero pinned genesis
identity and SQLite metadata; on a restart, it resumes the last committed
height. It fetches ONLY finalized blocks, verifies the node's finalized
head against block hashes, checks canonical height, actual parent linkage,
read-only hex-SCALE extrinsics, and revalidates the snapshot before committing
one batch atomically. If the node attempts to change a previously finalized
hash, the indexer **fails closed** instead of secretly rolling back finality.
Only an independently authenticated genuine DEVNIRA chain should be indexed.

Usage with a real local chain (mainnet is NOT launched):

```bash
python3 -m services.finalized_indexer --rpc http://127.0.0.1:9944 \
  --trusted-genesis 0x<actual-independently-verified-64-hex-genesis> \
  --db /private/path/dvn-finalized.sqlite --batch 100
```

Repeat at regular intervals via an owner-managed job (no built-in background
worker). To serve indexed records on the existing localhost-only API,
set `DVN_EXPLORER_DB=/private/path/dvn-finalized.sqlite` before starting
`python3 -m services.explorer_api`. Routes:
`/api/index/status`, `/api/index/block/123`, `/api/index/hash/0x...`.
The API opens this database **read-only** and keeps HTTP bound to
`127.0.0.1`. It does not expose private transactions.

Limitations and blockers: This is *not* a transaction decoder, account
indexer, tokenomics auditor, address search, public service, reorg-capable
unfinalized indexer, GPU proof verifier or production explorer. The API
does not cryptographically attest remote consensus; its security is only
as good as the independently pinned chain and trusted local node.
Our inert research chain is NOT a live mainnet, company genesis is absent,
so do not publish it as a network explorer yet. Gold/blue coin/website
design remains unchanged.
