# Stage 2 research: proof-side V2 Merkle-root and domain-bound nullifier

**Experimental / INACTIVE**. This module is deliberately not the live Quantus
wormhole verifier and does not make an independent DEVNIRA chain.

The pinned \`qp-zk-circuits\` cryptographic circuit candidate:
- Commits exact native 8-decimal input and conserves outputs plus fee.
- In-circuit computes a **one-level 4-ary sorted-Poseidon2 Merkle path**
  and constrains the publicly visible root to the recomputed root, rejecting
  invalid siblings and position hints.
- Produces a **network-tag-bound** Poseidon2 nullifier/public commitment
  with public root and output/fee, requiring a nonzero tag.
- Tests actual Plonky2 prove/verify and cryptographically rejects altered
  public root, siblings, claimed nullifier, network tag and fabricated amount.

**Critical remaining for V2 activation:**
1. Generalize the single-level test path to 1..MAX_DEPTH with historical root
   selection and canonical position/sibling handling. The single-level
   candidate does NOT authenticate membership in real production tree depth.
2. Bind real signing authorization and actual DEVNIRA chain genesis and
   verifier-version constants, not client-selectable tags.
3. Integrate root/nullifier inside the FULL V2 leaf proof AND both recursion
   batch layers. Replace V1 on-chain verifier with artifact-pinned proof
   processing, immutable nullifier anti-replay storage, finalized root
   window and exact fee semantics, with end-to-end adversarial tests.
4. Compile/review matching independent 8-decimal native/WASM runtime with
   exact genesis allocations and 12 Gregorian month cliffs. The real
   treasury beneficiary public SS58-190 address and launch timestamp must
   be provided by the owner and verified; NEVER fabricate them.
5. Run real node/GPU network integration and external security audit.

A root supplied as a *public* proof input is not authenticated to a real
blockchain merely because the proof checks its internal consistency. The
runtime must check root against its own accepted storage history and must
reject a previously used nullifier before paying. The test does not do that.

The original user-uploaded gold/blue logo and locked website files MUST be
preserved bit-for-bit. This cryptography change does not touch visual assets.
