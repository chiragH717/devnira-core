# DEVNIRA Stage2 separate native depth-16 Merkle state — NO HEADER / SEND

Builds on merged PR #29 and #30. Existing native balance escrow receipts, exact native V2 Poseidon leaf commitments and distinct depth16 4-ary Merkle state are updated in one FRAME storage transaction.

The V2 state storage includes DvnV2TreeCount, DvnV2TreeRoot, DvnV2TreeNodes by level/index, DvnV2TreeDirty and DvnV2TreeHistory keyed by block number. This is kept separate from the old V1 tree. A failed debit/root/receipt update rolls back all writes. Node hashing reuses pinned pallet_zk_tree::tree::hash_node, with 16 levels and zero-padding of absent siblings. The leaf-count cap is 4^16 and must exactly match the receipt index.

The internal current-root sibling witness returns 16 sets of three sibling hashes. Once additional leaves are appended, the newest witness is NOT a witness for the earlier root: archival node history is not implemented.

The wormhole pallet on_finalize snapshots the changed V2 root/count only as local block-end FRAME state. It does NOT set the canonical block header zk-tree root, prove independent finalized header history, or imply finality.

Genuine Rust FRAME tests exercise independently reconstructed 16-level roots, 3-leaf witness and sibling tampering, exact custody accounting, per-block snapshot, unchanged issuance/no V1 leaves, and rollback when funds or storage counts are invalid.

NOT PROVIDED: authentic independent finalized block-header root, replay-safe header history and archival witnesses, signed public deposit, benchmarked public dispatch weight, domain-bound approved production V2 verification key, active ZK atomic exit/nullifiers/fees native AND WASM, genesis, mining, wallets or security audit. Production Send remains disabled.
