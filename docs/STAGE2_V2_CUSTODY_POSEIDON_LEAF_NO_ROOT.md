# DEVNIRA Stage2: exact native custody receipt → V2 Poseidon leaf

**NO ROOT / NO SEND / NO MAINNET.**

This milestone composes the previously tested exact 8-decimal V2 ZK-tree native leaf hashing patch with the independently tested FRAME native escrow ledger.

For each **internal-only** actual native-token custody transfer, the same storage transaction writes:
- Escrowed exact native amount (u128, 1 DVN = 10^8 base units), recipient canonical account, per-recipient count, unique receipt ID.
- A 32-byte V2 Poseidon leaf commitment computed from those exact components, native asset tag 0, and a real hash primitive in pinned FRAME ZK tree source, checked byte-for-byte against the generic V2 leaf hash.
- V2 custody liability and monotonic counter. Any failure of transfer/receipt/hash/state aborts all writes and balance movement; no minted tokens.

Tests verify exact one-base-unit, distinct owner/count, no legacy 12-decimal leaf, unchanged issuance, underfunding rollback, corrupted cursors, and no hash on failed debit. This does NOT append those leaves into an independent 4-ary V2 tree or bind any commitment to finalized block headers. It does not produce a merkle witness, active proof verifier, signed deposit extrinsic, spendable withdrawal, or approved launch network. The actual upstream V1 tree and active V1 spend remain inert/blocked by DEVNIRA launch guards.

Next connected engineering gate: independent bounded append + Poseidon2 parent/hash tree + header root history domain, fixed trusted verifier and actual deposit-backed, atomic proof settlement in native AND WASM. Never announce mainnet or enable wallet Send based solely on hash receipts.
