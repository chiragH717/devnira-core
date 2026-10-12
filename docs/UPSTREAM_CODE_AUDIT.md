# Verified upstream code integration findings (2026-10-12)

Upstream: https://github.com/Quantus-Network/chain

Inspected source paths:
- `node/src/chain_spec.rs`
- `pallets/mining-rewards/src/lib.rs`
- `runtime/src/lib.rs`
- `Cargo.toml`, `LICENSE`, `README.md`

## Concrete incompatibilities that MUST be fixed before a DEVNIRA node can run

1. Quantus chain spec declares 12 token decimals, symbols DEV/HEI/QTC/PLK, and SS58 prefix 189. DEVNIRA requires DVN and the approved tokenomics reference uses **8 decimals**. Changing only UI metadata is insufficient: balance constants, existential deposit, fee scale, and runtime `Unit` must be audited.
2. Quantus development preset contains pre-funded accounts. DEVNIRA production genesis must have zero prefunded spendable balances; genesis governance authorities and storage initialization must be assessed separately.
3. Quantus mainnet chain spec uses `MAINNET_RUNTIME_PRESET` and `quantus` protocol ID, plus Quantus telemetry. DEVNIRA must create its own runtime preset, distinct chain ID and protocol ID, and remove inherited production endpoints.
4. Quantus `pallets/mining-rewards/src/lib.rs` computes reward as `remaining_supply / EmissionDivisor`, **not** DEVNIRA's 5 DVN multiplied by (399/400)^epoch. A new deterministic subsidy implementation must replace that formula and account for deferred miner payments and transaction fees.
5. Current standalone DEVNIRA Rust reference intentionally panics for epoch >=2. It is not deployable consensus code. Implement exact arithmetic in no_std using bounded big integers or a proven equivalent algorithm, and compare against independent Python test vectors.
6. Generate real chain spec from compiled runtime WASM and compute genesis state hash. A JSON proposal is not a genesis block.
7. Verify upstream license notices and all vendored third-party dependencies before copying source.

## Evidence and testing limits

The connected GitHub interface can read upstream text and write files to the DEVNIRA repository. This execution environment cannot reach GitHub over git HTTPS and does not have a Rust cargo toolchain. Consequently no upstream fork, node compilation, local node execution, genesis hash, GPU miner test, or local multi-node testnet has been performed here. These remain mandatory acceptance gates.

## Acceptance gates

- [ ] Pin upstream commit and import source with license notices
- [ ] Apply and review chain spec + runtime genesis changes
- [ ] Implement reward logic and exhaustive deterministic vectors
- [ ] Compile release binary and runtime WASM
- [ ] Derive and publish actual genesis hash from built node
- [ ] Mine valid QPoW blocks and test network isolation
- [ ] Verify NVIDIA and AMD separately
- [ ] Run local multi-node sync and reorganization tests
