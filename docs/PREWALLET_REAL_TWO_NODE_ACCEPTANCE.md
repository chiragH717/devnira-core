# DEVNIRA: actual two-node development test acceptance

Builds on merged PR #36, avoiding any re-run of isolated PR #33–35 proof tests. The GitHub Action assembles the combined pinned DEV source once, builds a real native+embedded-WASM node, then launches two localhost node processes with separate databases.

Five new checks in one batch:

1. Both real processes use shared nonzero DEV genesis, precise runtime ID, tokenDecimals 8, tokenSymbol DVN and SS58 190, with two-way P2P connections.
2. Both RPCs expose the same post-genesis finalized block hash. Height zero is a FAIL.
3. The real finalized qp_header has parentHash, stateRoot, extrinsicsRoot, digest and zkTreeRoot fields. Both nodes agree at a common finalized height.
4. The second process is restarted using its existing database, rejoins node A and re-reads the same finalized block hash and full header with unchanged ZK root. No finalized-height regression.
5. Negative tests reject incompatible chain identities, absent peers, genesis-only claims, fork hash disagreement, tampered V2 header fields and invalid data.

No signed transfer or wallet key material is generated. A successfully compiled candidate node does not constitute a successful two-node finality test. If the current dev consensus cannot finalize post-genesis blocks, the workflow MUST FAIL rather than invent a pass.

This is LOCAL DEV network evidence only, not independent production finality, historical membership witnesses, active approved verifier keys, custody-backed ZK payout, genuine GPU mining, company treasury or mainnet.