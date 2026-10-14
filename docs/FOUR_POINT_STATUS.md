# DEVNIRA four-point integration status (2026-10-14)

**Status: PRE-RELEASE DEVELOPMENT. NOT MAINNET. NOT A COMPLETE SIGNING WALLET.**

Approved consensus policy: independent DEVNIRA Layer-1; QPoW/Poseidon2; 12-second target; eight decimal places; 100M maximum DVN; 90M DVN budgeted exclusively to mining; 10M in ONE company-controlled treasury (3M unlocked at genesis, 7M locked to 12 exact Gregorian month cliffs). The company's real public signing address and genesis launch timestamp are not currently supplied. Do not invent these and never commit private keys or recovery phrases.

## 1 — Native ZK (actual build candidate verified; activation BLOCKED)

- Pinned upstream Plonky2 and FRAME sources have compiled/tested native 8-decimal u64/54-bit amount commitments, Poseidon2 golden vectors, one-base-unit sensitivity, 100M cap, and input = output1 + output2 + fee conservation with negative inflation tests.
- Proven cryptographic foundation does NOT mean the operational V1 leaf/prover/aggregator/withdrawal verifier has been fully replaced. Active production path still needs matching V2 recursion, aggregator public input encoding, nullifier/withdrawal settlement and anti-replay review.
- **Do not change UNIT to 1e8 and deploy with Quantus's active V1 proof system.** The fail-closed production gate deliberately rejects this mismatch.

## Latest Stage 2 V2 decoder update — 2026-10-14

- The pinned external qp-zk-circuits repository now accepts an **opt-in** exact-u64 amount decoder spanning the single **leaf**, **private-batch aggregation** and **public-batch aggregation** public-input layouts. The patch applies to the real `qp-wormhole-inputs` Rust crate, not merely a standalone Python mock. Amounts differing by 1 base unit remain distinct; malformed canonical Goldilocks values, overcap/negative conservation and nonzero private-batch padding are rejected.
- GitHub proof-inputs candidate CI **#2 passed**, including native Rust unit tests and wasm32v1-none/no_std compile: https://github.com/chiragH717/devnira-core/actions/runs/38538772966
- **Combined** Plonky2 bounded native Poseidon2 leaf/proof tests, exact fee/value conservation and both V2 batch-input decoders passed in **zk-proof-input-v2 #13**: https://github.com/chiragH717/devnira-core/actions/runs/38538996054
- **Critical cross-repo mismatch remains:** pinned Quantus chain `Cargo.toml` links to `qp-wormhole-*` **4.3.0**, while pinned external `qp-zk-circuits` source builds its proof crates as **4.4.0**. The current active verifier and both recursive wrapper circuits still use V1 `u32` quantized values, not V2 `u64` base units. In particular, output account sums are range-checked to 32 bits in the upstream private-batch circuit, and canonical verifier artifacts are pinned to old V1 circuit hashes. A successful V2 parser test CANNOT make this safe.
- **No automatic 12-to-8 runtime switch.** Full V2 activation must migrate leaf proof, private/public recursive circuits, prover input witnesses, verifier keys/artifact hashes, on-chain settlement and ZK tree root coherently, and retest all negative cases before activating the 8-decimal runtime and genesis.
- **Additional fail-closed guard shipped:** `scripts/patch_dvn_runtime_units.py` now refuses 8-decimal native-runtime source mutation even after superficial scale/u32 edits if pinned proof crates still link Quantus V1 `4.3.0` or any required crate version is absent. Dedicated negative regression tests passed in [Reference Checks #257](https://github.com/chiragH717/devnira-core/actions/runs/38539441386). The `4.4.0` source parser candidate is *not* equivalent to an active V2 verifier or an automatic dependency upgrade.
- **Stage 2 remains incomplete.** Developers should not call V2 public inputs an active V2 proof/verifier, nor present this as a mainnet approval.

### Newly verified: native-u64 Plonky2 aggregation and overflow-safe BPS (development only)

- `scripts/patch_zk_v2_aggregation_amounts.py` injects an *opt-in* real Rust Plonky2 module into the **pinned 4.4.0 upstream aggregator workspace**, alongside the existing V2 Poseidon2 leaf, fee-conservation circuit and native u64 leaf/private/public-batch parser. Existing V1 recursive circuit and verifier keys stay untouched.
- Actual `cargo test` creates, verifies and rejects private-batch and public-batch **54-bit native DVN** amount proofs. Aggregated input, output and total settlement are capped at exactly 100M DVN, including one-base-unit negative cases.
- **Critical security fix:** Goldilocks is about 1.84×10¹⁹; a maximum 8192-slot public wrapper can add far more than this even when each account stays under 100M DVN. The V2 gadget checks **every prefix sum** against the 100M cap, eliminating modular wraparound that a final-sum-only check could miss.
- **Actual fee-rate proof:** an amount up to 10¹⁶ times 10,000 BPS can exceed Goldilocks. The new gadget splits multiplication into exact 32-bit low/high limbs, carries safely, checks high/low borrow and enforces `outputs×10000 <= inputs×(10000−bps)`. A separate validated-u128 preflight rejects malformed user witnesses *before* invoking Plonky2's panic-prone range-check generators.
- Native V2 proof tests include 100M DVN fee arithmetic, incorrect fee/BPS rejection, invalid output inflation, oversized batch rejection, and **cryptographically tampered payout or BPS public-input verification failures**. [Real Aggregation Proof Build #7 — PASS](https://github.com/chiragH717/devnira-core/actions/runs/38541842020).
- Single combined `zk-proof-input-v2.yml` workflow now runs V2 leaf/Poseidon2 circuit, amount parser and aggregate fee proof tests together against the pinned source and compiler. This combined job's success must be verified separately; a standalone green aggregator result does NOT establish an active recursive verifier.
- **Still BLOCKED:** production 4.3.0 V1-to-4.4.0 V2 proof compatibility, native leaf/recursive verifier artifact hashes, public/private batch wrappers, settlement nullifiers, genuine independent eight-decimal runtime WASM/genesis, signing send wallet and physical GPU network tests.

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
