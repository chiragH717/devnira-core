# DEVNIRA single-run integration setup

Workflow: [DEVNIRA unified integration and release gates](../.github/workflows/unified-setup.yml)

## What this actually runs
1. Python and Rust **reference** tests for issuance, beneficiary allocation, calendar-month vesting, and the 8-decimal encoding preflight.
2. Creates a Windows `DEVNIRA-Node-Monitor.exe` artifact. **This is read-only diagnostic software, not a funds wallet.** It cannot create accounts, sign transactions, receive tracked funds, show balances or enforce lockups.
3. Downloads upstream Quantus source, applies development identity metadata, and checks DEVNIRA production prerequisites. The check is intentionally **expected to fail currently**: source remains 12-decimal and upstream ZK leaves are incompatible with DVN 8-decimal accounting. It also lacks approved DVN mining-subsidy and independent mainnet genesis.
4. The release gate cannot pass unless all other jobs pass; even if it passes, additional node compilation, two-node consensus/mining tests, hardware GPU tests and security review are required.

## Definition of production completion
- Integrate deterministic miner-only 90M-DVN issuance ledger and emission schedule in actual FRAME runtime, including deferred rewards, fee reissue and ZK leaf quantization.
- Migrate 8-decimal semantics across runtime, signed transfers, ZK circuits/provers, wormhole leaf storage, deposits, balance display and mining. Require cross-layer tests.
- Generate independent genesis with **user-approved public beneficiary addresses and allocations**, exactly 3M liquid DVN and 7M locked DVN; enforce 12 calendar-month unlocks on chain, checking treasury and existential deposit accounting separately.
- Implement, test and package a secure Windows signing wallet using the actual DEVNIRA address/key format. No unreviewed private-key storage.
- Successfully compile native and WASM runtimes, verify independent genesis and conduct two-node sync, reorg, 12-second PoW, rewards, vesting unlock and wallet transfer tests. Verify NVIDIA and AMD mining on actual hardware.
- Publish reproducible binaries and hashes only after verification.

## Current status
**NOT COMPLETE; NOT MAINNET READY.** A successful Windows monitor artifact or reference test suite does not mean DVN mainnet is operational.
