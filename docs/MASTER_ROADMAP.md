# DEVNIRA / DVN — full product, infrastructure and launch roadmap

**Updated 2026-10-14. Status: Stage 2 IN PROGRESS; 8-decimal independent DEVNIRA mainnet NOT RELEASE READY.**

This document covers the **whole product** — not only the blockchain code. Percentages below are **subjective planning estimates**, NOT test coverage, measured workload, completed percentage from GitHub or investment claims. They are explicitly separate from the production release gate.

## Immutable approved business and chain specification

- DEVNIRA (DVN), independent Layer-1, Quantus QPoW/Poseidon2-derived PoW, 12-second target, eight decimals, SS58 network prefix 190, company website target `devnira.co`.
- Total 100,000,000 DVN maximum; only 90,000,000 DVN issued through mining.
- Company/team/investor allocation 10,000,000 DVN at genesis: exactly 3,000,000 liquid in ONE company-owned account and 7,000,000 locked in twelve immutable calendar-month cliffs. Eleven equal base-unit payouts of 58,333,333,333,333 and final payout of 58,333,333,333,337.
- Subsidy starts at 5 DVN and declines by 0.25% each 50,000 blocks with integer-only accounting; 90M miner-only issuance cap. Fees are not new minted mining emission.
- NEVER insert a test/public mnemonic as real company custody; generate private keys on an offline trusted company device, prove ownership using a public signed challenge and do not commit secrets.

## Full scope dashboard (engineering estimate only)

| Product / component | Planning estimate | Verified development evidence | Mandatory remaining work |
|---|---:|---|---|
| Economics and allocation specification | 85% | Python/Rust exact issuance and company 3M/7M policy checks | Enforce issuance and 12-month schedule in the actual 8-decimal live runtime |
| Active ZK V2 proof migration | 55% | Real native-u64 Poseidon2 leaf proof, fixed-key recursive Plonky2 proof and public verifier artifacts; [PASS](https://github.com/chiragH717/devnira-core/actions/runs/38546765419) | Upgrade on-chain V1 leaf, full private/public recursive batch, prover, aggregator and verifier artifacts together; negative withdrawals/nullifiers/anti-replay |
| Development-node isolation | 75% | Native node + embedded WASM built; foreign Quantus live chain IDs rejected; [PASS](https://github.com/chiragH717/devnira-core/actions/runs/38545679156) | Independent DVN testnet node binary and actual genesis network, bootnodes, peers |
| Independent 8-decimal runtime and genesis | 15% | V2 runtime conversion patch & off-chain genesis audits; FRAME vesting-pot prototype | Replace 12-decimal active runtime coherently; audited on-chain 10M issue/no foreign premine; unique chain spec and signed company account; trusted genesis and WASM hashes |
| Miner subsidy and 12-month on-chain vesting | 55% | Source-level FRAME reward/vesting candidate compiled/tested in developer workflows | Active 90M miner-only state accounting, exact release and all cross-pallet supply invariants in actual 8-decimal chain |
| Windows wallet | 30% | SS58-190 receive + genesis-pinned finalized balance **read-only** EXE; native Dilithium87 ownership challenge | Secure encrypted key management, transaction SCALE signing, fee/nonce, Send, Receive, balance/locked balance under actual network, installer/code signing |
| Android wallet | 0% | No Android app or release in the core repository | Secure Android Keystore-based custody, verified chain pinning, receive/send, restore/backups, native signing, UI, build/publish |
| GPU miner source | 40% | Pinned upstream CUDA + WGPU/Vulkan sources compile/typecheck | DEVNIRA independent protocol compatibility; real NVIDIA and AMD GPU block/hash/shares, difficulty, payout |
| Two-node live GPU testnet | 0% | Two-node RPC validator script exists (no hardware/network execution evidence) | 2 distinct synced peers on one independent genesis; actual blocks, rewards, finality, invalid proofs/forks/reorg and restart tests on physical hardware |
| Mining pool | 5% | Offline, non-consensus share accounting preview; no miner server, verifier or payouts | Miner auth/job/share protocol, vardiff, duplicate/rejected shares, fair pooled payout and accounting, payouts, pool stats, security and deployment |
| Block explorer | 10% | Genesis-pinned local read-only RPC API and raw block lookup UI candidate; no indexer | Canonical indexed block/transaction/account/reward data; search, real-time status, fees, mining/issuance charts, API, UI, explorer hosting |
| Company website `devnira.co` | 15% | Responsive static frontend source with truthful release disclaimers; no verified deployment | Domain/DNS/TLS, responsive pages, downloads, roadmap, tokenomics, wallet/mining tutorials, explorer/pool links, SEO, privacy/security disclosures |
| Public RPC, indexer and APIs | 10% | Localhost RPC read-only parsing and test scripts | Independently deployed RPC endpoints, HTTPS/WSS, caching/rate-limits, indexed wallet/explorer APIs, stable endpoints and monitoring |
| Security and product release | 5% | Fail-closed release checks and some negative tests | Independent consensus/ZK/economics audit, custody threat model, fuzz/DoS, reproducible builds, signed installer & binaries, incident response |
| CI and automated integration | 65% | Many source/FRAME/WASM/proof candidate green GitHub Actions and fail-closed production gate | True active 8-decimal end-to-end CI, dedicated two-node GPU and Android/mobile build, signed release pipeline |
| Documentation and launch readiness | 40% | Technical audit notes, tokenomics and release blockers recorded | User-facing whitepaper, public technical spec, SDK/API docs, operator guides, launch FAQs, transparent treasury and release policy |

**Arithmetic mean of these 16 indicative values: ~32%; ~68% planning scope remains.** These estimates must never be presented as chain safety, revenue/commercial or an engineering deadline. Operational **mainnet readiness remains blocked**, regardless of averaged numbers.

## Stage 2 exit criteria — all must pass

1. End-to-end **ACTIVE** leaf → private aggregation → public aggregation → settlement verifier and same digest/proof protocol in pinned source and runtime; reject tampering, replay, oversupply, false withdrawals, wrong keys/circuits.
2. Independent `UNIT=100_000_000` WASM and native runtime; proper fees/deposits, ZK leaf quantum 1 base unit, canonical SS58-190, 100M cap, no quantized V1 exits.
3. Exactly 10M genesis issuance to the company-controlled public address and sovereign 7M vesting pot; twelve immutable calendar cliffs, no extra existential-deposit issuance, no test accounts; governance and emergency paths audited.
4. Unique DVN chain ID, protocol, runtime hash, genesis hash and build spec; independent two-node state sync, local-to-live upgrade policy, negative cross-network proof.
5. End-to-end Dilithium87 **signed real transaction** (NOT only arbitrary-message custody signature) with fee/nonce/finality and signed Windows wallet.

Stage 2 cannot be called finished until these conditions pass. Additional physical GPU, Android, explorer, pool, website and release audit stages remain required even after Stage 2.

## Stage 3 — real mining testnet / wallet & infrastructure

- Independently started Node A and Node B use the same final DVN genesis and exchange blocks/finality, share fees, reward budgets and recovered state.
- Real CUDA NVIDIA and WGPU/Vulkan AMD machines complete valid 12-second-target QPoW integration (observed time varies with difficulty), with invalid shares and reward disputes safely rejected.
- Wallet pays a testnet signed transfer and correctly displays ledger and locked vesting state from independently verified chain RPCs.
- Monitoring, seed nodes, trusted DNS/TLS, public testnet faucet with **test tokens only**, backup/recovery and pool server validation occur before third-party miner onboarding.

## Stage 4 — full public product

**Website `devnira.co`**: Homepage; About/How it works; 100M supply and 10M company vs 90M mining chart; GPU mining setup; Windows and Android wallet download pages with signed binaries/checksums; Explorer; Pool; technical docs/whitepaper; roadmap; network status; contact/support; clear risks/privacy/terms. Domain registration/hosting/TLS are **not verified**, so do not assert site is live.

**Explorer**: Indexer from authenticated independent DVN RPC; canonical block and transaction ingestion with reorg handling; finalized/unfinalized status, account balances and transfers, locked vesting display, miner addresses/PoW difficulty, issuance vs supply cap, block reward/fees, search, REST/WebSocket APIs, responsive public interface, telemetry, caching/recovery and a verifiable production URL. It **cannot be completed honestly before real chain data is available**.

**GPU mining pool**: Actual jobs and shares validated against the independent node; pool difficulty/share expiry, reward distribution, duplicate/replay defense, worker accounts, balance/payout history, operational pool dashboard and pool compatibility instructions. No mainnet shares/payouts have been observed.

**Wallets**: Company-first production-grade custody/multisig policy with offline recovery; Windows signed/send/receive; Android independent security review and tested release. Hardware wallet support is optional future scope, not presently implemented.

**Launch**: Independent security review and remediations; reproducible published source/native/WASM builds and checksums; third-party two-node/network acceptance, actual GPU proof and rewards, explorer cross-check of genesis supply, public testnet and bug bounty; mainnet genesis/hash signed-off by custodians, honest disclosure of the 10% allocation. Do not announce mainnet until production release gate accepts external evidence.

## Human-dependent launch inputs still missing

| Input | Current status | What is safe to share |
|---|---|---|
| Real company treasury SS58-190 address | Not provided/verified; must be generated locally | **Public address and public signed ownership proof only** |
| Company custody operating model and backup owners | Not finalized | Public policy only; never keys/seeds |
| Mainnet UTC genesis timestamp | Not approved | Future timestamp after audits and testnet readiness |
| Domain `devnira.co`, legal/branding/hosting decisions | Not verified | Public brand assets, DNS/operator instructions |
| Actual physical NVIDIA/AMD GPU hardware / test network | Not available in GitHub-hosted CPU runners | Hardware specifications and publicly safe test metrics |
| Bootnodes and public RPC/hosting choices | Not deployed | Public URLs and operational decisions, no private access credentials |

## Highest priority engineering order

**ZK V2 on-chain activation → independent 8-decimal runtime/genesis → company signing wallet → true two-node CUDA/AMD mining → pool + explorer backend → website/frontends + Android → complete audit/release.**

A combined static website, fail-closed local RPC explorer and offline pool accounting **development candidate** is documented in [PUBLIC_PRODUCT_CANDIDATES.md](PUBLIC_PRODUCT_CANDIDATES.md); this does not implement any active miner pool or public explorer deployment.

Existing GitHub Actions PASS is authentic evidence of each named **development test**, not proof that unfinished systems are ready. Keep `release_evidence_gate.py` and production build fail-closed.
