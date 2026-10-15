# Stage 2 multi-component delivery — actual 22PI proof + FRAME batch replay

This change extends the **same Plonky2 22-felt proof**, rather than adding
another incompatible research public-input layout. It is the V2 source
originally pinned at qp-zk-circuits
`fa5f57dc1a1b755ff1b7f4fdb4309e1e06669ba2`.

## Component A — secret-owned actual native proof with Merkle depth 1,2,3

A single circuit links the private spend secret and derived funding account,
the nullifier, native u64 exact 8-decimal values/fee rounding, 4-ary sorted
Poseidon2 leaf-to-root membership and a complete Poseidon2 historical header
preimage. Compiles circuits for depths 1,2,3; Rust Plonky2 witnesses verify
valid paths and reject forged deep sibling, position, root, secret, header,
fee/rate and extra issuance. The 22 public fields are identical at all three
tested depths. **Still not a full-depth or production recursive circuit.**

## Component B — read-only REAL FRAME on-chain 22PI batch admission

The actual pinned upstream FRAME Wormhole checks every leaf's 22 field
metadata against stored real historical block hashes and `UsedNullifiers`.
The extra bounded (1..64) batch check detects duplicate nullifiers *within
the same batch*, shared historical block hash+height and cumulative exact
native totals below the 100M DVN supply cap. Existing tests additionally
check no coins are transferred, no nullifier is written, persisted double
spends rejected and invalid reference blocks rejected.

## Component C — one GitHub CI release gate for both

One workflow runs actual Rust Plonky2 proof tests AND actual FRAME pallet
tests on exact upstream pinned commits; fake source-shape unit tests are
supplemental. Both jobs must be green before merging.

**No on-chain V2 spend can be activated from this PR**. Unresolved:
production-depth circuits, recursive authenticated private/public
aggregators, production pinned verifier key and wasm compatible proving;
cryptographic association of batch outputs to each verified individual
proof; atomic nullifier state changes and payouts; active 8-decimal
spendable runtime and genuinely independent 3M/7M/90M Genesis; secure
Windows/Android signed wallet, real GPUs, public pool/explorer/RPC,
original user-approved Gold/Blue website deployment and independent audit.

Approved DVN tokenomics or final coin/logo design must NOT be altered.
