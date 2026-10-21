# DEVNIRA post-merge real network: bounded finalized ancestry evidence

This expands local pre-wallet validation from one matching finalized header to as many as 8 consecutive post-genesis headers. Every observed height must match both nodes' canonical block hash, qp_header number, digest, parentHash, stateRoot, extrinsicsRoot and zkTreeRoot. Every parent is independently looked up via chain_getBlockHash(n-1); the chain reaches the trusted local DEV genesis at height 1. Before and after an actual same-database node restart, the entire original historical observation must be identical.

Five new checked properties: non-genesis requirement, independent canonical parent ancestry, complete header field comparison including ZK root, unchanged finalized history after restart, wrong genesis / malformed hash / fork / altered root rejection. Bounds 1..64 avoid large RPC DoS.

**Important distinction:** V2 header selector remains DISABLED in the development runtime. A qp_header zkTreeRoot field appearing in a finalized block does not prove the independent V2 tree root is enabled or that V2 witnesses can be spent. This stage does not cryptographically recompute header Poseidon hashes, implement signed transfers, prove economic consensus, production verifier keys, custody-backed ZK settlement, physical GPU mining, wallets, company Genesis or mainnet.

CI green means only that **local** proof of contiguous imported/finalized block observations and restart integrity succeeded; it is not a public finality certification.