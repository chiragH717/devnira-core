# DEVNIRA four-point integration status (2026-10-14)

**Status: PRE-RELEASE DEVELOPMENT. NOT MAINNET. NOT A COMPLETE SIGNING WALLET.**

Approved consensus policy: independent DEVNIRA Layer-1; QPoW/Poseidon2; 12-second target; eight decimal places; 100M maximum DVN; 90M DVN budgeted exclusively to mining; 10M in ONE company-controlled treasury (3M unlocked at genesis, 7M locked to 12 exact Gregorian month cliffs). The company's real public signing address and genesis launch timestamp are not currently supplied. Do not invent these and never commit private keys or recovery phrases.

## 1 — Native ZK (actual build candidate verified; activation BLOCKED)

- Pinned upstream Plonky2 and FRAME sources have compiled/tested native 8-decimal u64/54-bit amount commitments, Poseidon2 golden vectors, one-base-unit sensitivity, 100M cap, and input = output1 + output2 + fee conservation with negative inflation tests.
- Proven cryptographic foundation does NOT mean the operational V1 leaf/prover/aggregator/withdrawal verifier has been fully replaced. Active production path still needs matching V2 recursion, aggregator public input encoding, nullifier/withdrawal settlement and anti-replay review.
- **Do not change UNIT to 1e8 and deploy with Quantus's active V1 proof system.** The fail-closed production gate deliberately rejects this mismatch.

## 2 — Independent genesis (economics and pot safety unit/FRAME tests; launch BLOCKED)

- Approved single company treasury has exactly 3M spendable + 7M escrowed via 12 noncancelable genesis grants in opt-in FRAME vesting patch; no extra existential-deposit minting.
- The escrow address is no longer caller-supplied: `spec/vesting_pot.py` derives the FRAME `PalletId(*b"qvesting")` sovereign AccountId32 (`b"modlqvesting"+20\x00`) and encodes it with DEVNIRA SS58 prefix 190.
- Genesis audits now **reject a fake 7M funded account even if total balances sum to 10M**; only the correct FRAME account can fund vesting claims.
- No company's independently verified live public address, actual eight-decimal runtime WASM/genesis hash or real mining-network identity have been minted, built or activated. Off-chain manifests are not proof of a real chain.
- Production build pulls the *pinned* upstream commit and hard-blocks before compilation without actual genesis address/timestamp and source-level runtime+ZK audits.

## 3 — Windows Wallet (receive and balance preview compiled; SEND BLOCKED)

- Native Rust Dilithium87 company-custody challenge sign/verify and 3M/7M public test manifest passed using the **published unsafe test mnemonic** only.
- Windows GUI now supports native SS58 190 *public* Receive Address validation and copying, exact eight-decimal Free/Reserved balances, and finalized block pinning; the reader queries `System.Account` via 32-byte key derived from `Twox128(System)||Twox128(Account)||Blake2_128Concat(AccountId32)`.
- It rejects remote/nonlocal RPC, missing or mismatched pinned genesis, 12-decimal foreign runtime/chain properties, malformed SCALE storage, unexpected account layout, and balances over the hard cap. It never stores private keys.
- Windows PyInstaller `DEVNIRA-ReadOnly-Wallet-Preview.exe` built with tests and SHA-256 artifact at: https://github.com/chiragH717/devnira-core/actions/runs/38535533878
- **Send, transaction SCALE payload signing, fee/nonce management, encrypted signing custody, broadcast and Android wallet are NOT implemented.** There is no verified independent mainnet RPC to show real balances yet.

## 4 — NVIDIA/AMD GPU PoW (source compile succeeded; actual GPU mining BLOCKED)

- Pin `Quantus-Network/quantus-miner` to Git SHA `c7838cbc86f7d74477da1771139f377a8e438072`. Confirmed miner source exposes native NVIDIA CUDA and cross-platform wgpu Vulkan/DX12 (including AMD), using qpow-math and Poseidon2.
- Upstream miner Pow-core tests plus typechecks for CUDA and wgpu engines passed in **GPU-less Ubuntu CI**; do NOT confuse code compilation with a real GPU share or mined DVN block.
- Hardware tests must use independent DVN node(s), actual NVIDIA and AMD devices, correctly firewalled miner QUIC service with TLS fingerprint and auth token from protected files, verified real PoW shares/rewards, two-node finalized genesis/blocks, and invalid proof/fork tests.
- **Never publish miner auth tokens, reward preimages, TLS private material, company seed or raw GPU device secrets to GitHub.**

## Evidence links and next gates

- Windows read-only EXE: https://github.com/chiragH717/devnira-core/actions/workflows/windows-wallet-preview.yml
- ZK V2 proof source and tests: https://github.com/chiragH717/devnira-core/actions/workflows/zk-proof-input-v2.yml
- Exact FRAME genesis pot: https://github.com/chiragH717/devnira-core/actions/workflows/exact-genesis-pot.yml
- CUDA / AMD candidate: https://github.com/chiragH717/devnira-core/actions/workflows/gpu-miner-source.yml
- Full developer candidate: https://github.com/chiragH717/devnira-core/actions/workflows/four-component-build.yml
- **Separate production build/readiness**: `production-build.yml` + `unified-setup.yml`, which intentionally FAIL until independent eight-decimal ZK proof/genesis evidence is present.

Production readiness cannot be certified by green reference/source workflows, by a published test mnemonic, by a mock/fabricated genesis, or by an unexecuted two-node/GPU script. **No new coins have been allocated or transferred to a real company wallet.**
