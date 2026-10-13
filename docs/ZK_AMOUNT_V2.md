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
