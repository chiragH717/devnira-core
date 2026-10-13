# Stage 2 — Quantus core integration tracker

Status: **IN PROGRESS — NOT A RUNNABLE DEVNIRA BLOCKCHAIN**.

## Upstream verified

- Upstream: https://github.com/Quantus-Network/chain (main branch; pin commit before forking).
- Root LICENSE text grants broad MIT-style reuse subject to copyright/license notice retention.
- Workspace manifest declares `license = "MIT-0"`; reconcile root and per-crate notices before distribution.
- Upstream is a Rust workspace containing `node`, `runtime`, `client/consensus/qpow`, `pallets/qpow`, `pallets/mining-rewards`, `miner-api`, `qpow-math`, and related dependencies.
- Upstream README requires nightly Rust; upstream local development uses `quantus-node --dev` and has pre-funded development accounts. DEVNIRA mainnet must NOT inherit any prefunded genesis accounts.

## DEVNIRA decisions

Name DEVNIRA, ticker DVN, 12s target, QPoW/Poseidon2 reference, 100M DVN cap, 0 premine, 5 DVN initial subsidy, 399/400 every 50,000 blocks, 8 decimals, 1-unit tail until cap.

## Mandatory implementation tasks (not yet completed)

1. Pin upstream commit and vendor/fork with original copyright and third-party notices.
2. Audit existing chain-spec and runtime genesis allocation; make all mainnet allocations zero except legitimate runtime storage structures.
3. Generate unique chain ID, protocol ID, network keys, bootnodes, genesis hash and address-prefix strategy.
4. Locate and replace all network-specific identifiers and seed nodes; separate local dev/testnet/mainnet.
5. Implement exact deterministic epoch reward arithmetic with *no floating point* and test cross-language vectors.
6. Integrate emission logic into mining rewards pallet; verify issuance and fee handling and cap under reorgs.
7. Review 12-second slot timing, difficulty retarget, timestamp bounds, finality, PoW validation, miner API and RPC.
8. Validate GPU miner protocol on NVIDIA and AMD independently; do not assume existing Quantus miner is drop-in compatible.
9. Run reproducible build, integration, multi-node, adversarial and security tests.
10. Release a public testnet before mainnet.

## Important arithmetic caveat

The current Python reference uses large integers. The standalone Rust reference only supports the first two epochs; it intentionally fails for later epochs rather than silently producing a divergent reward. **Do not deploy** until a complete, bounded, cross-validated runtime implementation exists.

No node, network, miner, wallet or public chain is running from this repository.

## One-build FRAME candidate (2026-10-13)

`.github/workflows/stage2-combined-runtime.yml` applies **the reward subsidy/cap patch and immutable calendar-month vesting patch together** in the same upstream checkout. It runs FRAME tests for pending rewards, fee recycling, mining cap, twelve monthly cliffs and genesis-grant protection, then builds the native node and embedded WASM runtime. This prevents a green test in one patch from being mistaken for integrated runtime proof when another patch is missing.

**Scope:** This is a *development runtime candidate only*. It uses the upstream 12-decimal units, original ZK proof/circuit and testnet genesis. Passing CI does not make DVN mainnet. Stage 2 remains open until the 8-decimal proof migration, independent actual genesis, user-approved public beneficiary allocations, synchronized mining testnet and signing wallet are integrated and tested. Current CI result for the combined workflow is not yet confirmed.
