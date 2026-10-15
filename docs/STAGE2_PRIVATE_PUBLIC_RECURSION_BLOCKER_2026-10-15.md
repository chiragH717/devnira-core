# DEVNIRA V2 PRIVATE → PUBLIC recursion: blocker confirmed (2026-10-15)

**BLOCKED — do not merge #27, publish production verifier-key hashes, enable settlement or ship a signed wallet.**

## Reproducible evidence

Pinned source:
- ZK: `Quantus-Network/qp-zk-circuits@fa5f57dc1a1b755ff1b7f4fdb4309e1e06669ba2`
- FRAME: `Quantus-Network/chain@482c5b9e02bec0adc70797eade0a67f60baf2619`
- qp-plonky2 `1.6.0` from locked dependency, Rust `1.93.0`.

The full-depth 16-level 22PI leaf and **existing first-tier fixed-VK recursion** compiled and proved successfully in GitHub CI. New candidate two-tier circuit composition compiles, but proving a PUBLIC wrapper over authentic PRIVATE wrapper proofs fails in qp-plonky2's `iop/witness.rs:75` at `set_extension_targets`:

```
assertion left == right failed
left: 264
right: 263
```

The mismatch is a FRI opening-target length against proof opening length while populating the second-tier recursive proof witness. It was independently reproduced in the two-tier CI workflow. Merely changing the intermediate private wrapper to avoid redundant range-check gadgets **did not** fix the mismatch.

Confirmed failures:
- `https://github.com/chiragH717/devnira-core/actions/runs/38785505810` — original private wrapper, native PUBLIC-of-PRIVATE test FAIL.
- `https://github.com/chiragH717/devnira-core/actions/runs/38787210740` — minimal authenticated private wrapper still FAILs with **the same 264/263 mismatch**.

The previous first-tier verified native FRAME compatibility still stands: `https://github.com/chiragH717/devnira-core/actions/runs/38766330018` (PR #26, merged), but **it does not prove the two-tier pipeline**.

## Correct engineering resolution

1. Reproduce and diagnose the *exact* FRI opening layout mismatch in the locked `qp-plonky2` v1.6.0 recursive target/proof builder (check target `FriOpenings` construction against nested `Proof` serialization, common circuit data and lookup/oracle layout). Add a minimal upstream regression test that fails BEFORE changing code.
2. Patch/fork and pin the actual upstream verifier/prover dependency source revision or upgrade to a demonstrably compatible, reviewed release. Do **not** truncate/pad witness openings, remove `debug_assert_eq!`, disable proof verification, or accept attacker-controlled verifier data to force a green result.
3. Verify truly authentic two-level private/public proofs, duplicates, foreign private keys, changed historical header, and exact 8-decimal native fees. Re-export real public/private `verifier_only.bin`, common data, immutable source pins, and SHA-256 hashes. Public hashes are *candidate* material, not approvals.
4. Only once these exact proofs pass the **same pinned FRAME native and WASM** runtime and a separate security/economic audit, pin production-approved VK commitments into a real *non-test* FRAME runtime. Do not activate `#[cfg(test)]` escrow helpers or treat a mocked `BlockHash` as independent finalized DVN history.
5. Production is further blocked by 12-decimal V1 deposit recorder still present in the inert 8-decimal node, lack of independently funded DVN deposits/escrow, true finalized historical Merkle state, signed wallet and spendable independent genesis.

No Gold/Blue original brand, treasury allocation, genesis keys or actual chain funds were changed.

**Engineering interpretation:** real source work was staged in #27, but **ACTIVE PRIVATE/PUBLIC PRODUCTION AGGREGATOR and APPROVED VK are NOT FINISHED**. Keep #27 unmerged until the exact new CI and security gates pass. Stop replaying old successful first-tier tests as if they prove this missing step.
