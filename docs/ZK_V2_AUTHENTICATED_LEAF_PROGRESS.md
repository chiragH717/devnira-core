# Stage 2 — 22-felt owner/nullifier/Merkle/header cryptographic integration

This update goes beyond earlier independent proof demos by composing **the
original pinned 4.4-era Quantus Plonky2 deposit-account secret derivation**,
the same pinned nullifier hash derivation, 8-decimal exact u64 DVN
input/output conservation, four-child Poseidon2 Merkle membership, and
the canonical **complete historical block-header Poseidon2 preimage**
into **ONE 22-public-input leaf proof**.

It uses the actual pinned `UnspendableAccount::constraints`,
`Nullifier::conditional_hash_binding`, and
`BlockHeader::conditional_block_hash_binding` from the original source.
The Merkle root feeds the header's zk_tree_root preimage before the public
block hash is calculated, avoiding the old unauthenticated client-chosen
root in the basic 22-felt layout candidate. It requires nonzero input,
nonzero block number, nonempty public payout accounts and exact native
amount conservation. Real Plonky2 valid and adversarial witness tests must
pass before considering it a completed **research** milestone.

**Strict production limitations:**

- Only **one Merkle level** is in this combined circuit; the separate
  multi-depth proof tests are still a different incompatible artifact.
- This research circuit now **proves correct rounded-down 4-bps fee** in
  exact 8-decimal base units, with an explicit 14-bit remainder, strict
  remainder < 10,000, and fee ≤ 4e12 so all multiplication stays well
  below the Goldilocks modulus. Real tests include fee/rounding tampering.
  The 4-bps rate is still a FIXED research constant, not full dynamic
  FRAME runtime fee governance or production withdrawal economics.
- It proves that the public header hash commits to this private root; only
  the future on-chain verifier may decide whether that hash matches a
  genuine finalized historical DEVNIRA header.
- Proof **does not** check on-chain already-used nullifier state, which
  must be atomically persisted with payouts by the verifier.
- Not connected to the recursive private/public aggregator, active 4.3.0
  on-chain verifier, 8-decimal spendable native/WASM runtime, wallet Send,
  company Genesis or public network. There is still **NO MAINNET**.
- Deterministic secret values in Rust tests are fixtures and must NEVER be
  used for company treasury custody.

All original user-approved gold/blue coin and website images remain
untouched. No invented genesis hash or public company account.
