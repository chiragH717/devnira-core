# DEVNIRA V2 PRIVATE → PUBLIC recursion: corrected diagnosis (2026-10-16)

**The previously reported nested FRI blocker was misdiagnosed. Production remains BLOCKED.**

## Verified new evidence

- Tested source: `0f79d6ff670cddd6b51df4756b801b608c9657fb` on PR #27.
- Integrated CI: https://github.com/chiragH717/devnira-core/actions/runs/38851923003
- Native prover job `116814819526`: SUCCESS.
- The actual depth16 22PI leaf → 24PI PRIVATE → 50PI PUBLIC proof is generated and cryptographically verified. Both private proofs refer to the same historical root and distinct nullifiers; duplicate and altered-output rejection pass.
- The previous `264/263` panic happens during assignment of a deliberately FOREIGN circuit proof, after the valid 50PI proof has been verified. That assignment was outside `catch_unwind`; the old logs had no stage markers/backtrace and did not establish that genuine nested proving failed.
- The fix includes foreign witness assignment and proving in the rejection boundary. It adds positive-stage markers and a backtrace. No opening arrays are truncated/padded, no assertions removed, no verification bypassed, no dependency upgraded, and no cryptographic circuit constraints weakened.
- This foreign-circuit case establishes incompatible-proof rejection; it alone is not a comprehensive same-shape wrong-key soundness proof.

The genuine private/public proof, verifier-only and common data are exported from that successful job. They are DEVELOPMENT evidence, never approved production keys.

## Downstream validation

FRAME proof-byte verification, actual balance/fee/nullifier settlement, replay and insufficient-funds rollback steps have succeeded in job `116815940482`. The same job's full native node + embedded-WASM release build succeeded on 2026-10-16 at 05:23:58 UTC (32m30s build). All 8 FRAME tests passed: 2 proof-byte compatibility, 4 atomic escrow/replay/tamper/rollback, 2 private/public settlement/history tests. The complete integrated run finished SUCCESS. Test-only settlement is excluded from WASM via `cfg(test)`; compiling that node does NOT mean settlement executed inside WASM.

## Remaining production boundary

Escrow integration is `#[cfg(test)]`; no production dispatchable or active V2 verifier exists. The node remains NO SEND. Mock historical `BlockHash` and pre-funded test escrow do not prove independent chain history or real deposit custody. The V1 deposit recorder still has `10^10` quantization. Dynamic fee policy, production domain separation, bounded dispatch/weights, consensus-pinned reviewed VKs, exact native deposit commitments and signed testnet transactions must be integrated before activation. Independent external review remains required.

## Historical failure runs (diagnosis superseded, evidence retained)

- https://github.com/chiragH717/devnira-core/actions/runs/38785505810
- https://github.com/chiragH717/devnira-core/actions/runs/38787210740

Do not repeat those old tests or patch qp-plonky2 on the assumption of a demonstrated upstream nested FRI bug. The new stage-specific evidence identifies a negative-test harness failure.

No Gold/Blue assets, company treasury address, genesis timestamp or production funds changed.

## Public development verifier fingerprints

Source `0f79d6ff670cddd6b51df4756b801b608c9657fb`, run `38851923003`, prover job `116814819526`, artifact `12025987018`. SHA256 from the successful prover job:

| File | SHA256 |
|---|---|
| `private-v2-24pi-vk.bin` | `559d8dbbb045ae9a8afdb01fd12c552aca51e88ca89b8ef90f61e2b44c7929f8` |
| `private-v2-24pi-common.bin` | `2077aeef0cea813aa393a5ef6926fc09f1481378f95bf7514270342c8c77d31b` |
| `public-v2-50pi-vk.bin` | `7029e733370b52d7f0549a8e097062257c3da8c0a031f39af8b9113ec06ae564` |
| `public-v2-50pi-common.bin` | `d1e8df0c83a346063e34c4b2de12b1959c47051c06fe51598ccbb64e0db12e16` |

These identify this development output only. `config/dvn-v2-private-public-vk-candidate.json` intentionally retains null approved candidate pins and false production activation flags. Hashes do not constitute an independent audit or a trusted runtime key installation.
