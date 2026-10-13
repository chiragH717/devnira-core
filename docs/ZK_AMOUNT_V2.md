# DEVNIRA ZK V2 native amount encoding design

**Proposal, not deployed consensus.** The native DVN cap is 100,000,000 DVN at 8 decimals = `10_000_000_000_000_000` integer base units. The Goldilocks prime is `0xFFFFFFFF00000001` (about 1.84e19); the full DVN native supply is below that prime and below `u64::MAX`.

The upstream leaf commits a quantized `u32`, losing precision or range. Proposed V2 native amount: a **single canonical u64 Goldilocks field element**, represented as 8-byte little-endian. This preserves each 1e-8 DVN base unit and can represent the entire 100M-DVN supply without saturation. All native amount inputs must reject negatives, values above the DVN supply, and noncanonical field values. Reference encoder and boundary tests: `spec/zk_amount_v2.py`, `tests/test_zk_amount_v2.py`.

## Required integration before release
1. Modify `pallets/zk-tree/src/tree.rs` leaf hashing to commit canonical base-unit amount; remove the upstream u32-saturation and 1e10 scale-down for native DVN.
2. Update all corresponding `qp-zk-circuits` witnesses/targets, transfer proof serialization, prover, withdrawal verifier, amount arithmetic/range constraints and note/nullifier derivation. Leaf hash preimages must match on-chain and circuit bit-for-bit.
3. Audit **pallet-assets** separately: unlimited or independently issued assets cannot inherit the DVN native cap without deliberate per-asset rules. No silent saturating or truncation.
4. Update Wormhole fee, rewards and vesting payout quantum, in-flight proof formats, wallet key handling and generated RPC metadata for 8 decimals.
5. End-to-end roundtrip tests at 1 base unit, 5 DVN miner subsidy, monthly vesting instalments and 100M DVN cap; malicious out-of-range inputs must fail. Validate compatibility and genesis-only migration; never deploy V2 over a V1 network without a complete upgrade plan.

A Python roundtrip is **not** a ZK proof validation. Do not change the production safety gate on the strength of the reference alone.

## FRAME ZK-tree integration prototype — 2026-10-13

`scripts/patch_zk_amount_v2.py` now adds `devnira_amount.rs` **inside the upstream FRAME `pallet-zk-tree` crate**, exposing an exact `u64` native DVN amount encoder/decoder with explicit native-supply and Goldilocks canonicality checks. `zk-v2-codec.yml` automatically compiles and runs the new Rust tests in the real upstream pallet, plus Python patch regression tests. This is stronger than a disconnected reference crate.

**Critical:** The new module is **inactive** in the actual Poseidon2 leaf hash. It does not change `AMOUNT_SCALE_DOWN_FACTOR`, Wormhole `SCALE_DOWN_FACTOR`, ZK witness/prover/verifier, withdrawals, assets, or the 12-decimal runtime `UNIT`. The workflow explicitly asserts the old leaf hash stays unchanged. Its passing result, if attained, would confirm only isolated V2 codec compilation—not 8-decimal blockchain migration. Production safety gate remains expected to fail until the proof system is migrated end-to-end.

## Cross-layer V1 blocker audit (2026-10-13)

The official upstream chain workspace pins external `qp-wormhole-circuit`, `qp-wormhole-inputs`, `qp-wormhole-prover` and `qp-wormhole-verifier` crates at `4.3.0`. The Poseidon leaf preimage must match this separate proof stack; changing only native `UNIT` or adding a codec module leaves this core system at V1.

`scripts/audit_zk_migration.py` now inspects upstream runtime units/supply, ZK tree leaf truncation, Wormhole quantum, vesting payout constraints and external proof crate dependencies together. The candidate CI tests that **upstream V1 is explicitly rejected**. This is not the production V2 implementation. The current audit intentionally cannot mark a release safe until the proof packages are replaced and the audit evolves to validate an actually linked V2 circuit/prover/verifier implementation.

Before mainnet, fork or otherwise control the published proof-source crates, implement/cross-check exact native-amount field encoding and public input constraints, publish reproducible crate revisions, replace and pin every runtime and wallet dependency, and pass deposit -> V2 proof -> on-chain verify -> withdrawal integration plus malformed proof tests. No existing release candidate satisfies this.

## Direct circuit-source integration milestone — 2026-10-13

The actual public source for the ZK prover stack is [Quantus-Network/qp-zk-circuits](https://github.com/Quantus-Network/qp-zk-circuits), with distinct `wormhole/inputs`, `wormhole/circuit`, `wormhole/prover`, `wormhole/verifier`, and `wormhole/aggregator` crates. Its current workspace is **4.4.0**, whereas the chain currently pins the related crates at **4.3.0**. Changing only some crate versions is unsafe because compiled proving/verifying keys and public-input layouts must match.

`scripts/patch_zk_proof_inputs_v2.py` now applies a real-source, separate `devnira_v2` module to upstream `wormhole/inputs`. It models the exact `u64` input/output amounts and rejects noncanonical values, out-of-supply amounts, or outputs exceeding the input. `.github/workflows/zk-proof-input-v2.yml` tests the modified **real upstream Rust crate** and records its revision. This is a staged **input codec prototype only**. Production proof parsing remains V1 `u32`, and the leaf circuit/aggregation/public batch/verifier/actual chain remain V1. The new CI result has not yet been confirmed.

Production migration sequence: pin a single source revision/fork of all five proof crates; define one versioned field/amount format and canonical range constraints; migrate leaf witness, target constraints, public input types and private/public batch aggregator arithmetic; regenerate circuit/verifier artifacts; integrate exact same format in runtime/Wormhole and Windows wallet; test actual valid + invalid proofs end-to-end on isolated DVN genesis. No Mainnet readiness claim until then.
