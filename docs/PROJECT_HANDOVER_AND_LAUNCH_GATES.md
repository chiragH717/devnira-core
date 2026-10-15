# DEVNIRA (DVN) — Full Project Handover and Launch Blockers
**Status as of 2026-10-15 — mainnet NOT live, Stage 2 NOT complete.**

## Instructions for the next ChatGPT chat
The user speaks Gujarati; respond in Gujarati. Apply real GitHub source changes and inspect CI before calling a module complete. Do not give repeated planning and never confuse green candidate tests with a working global wallet or deployed network. Repo: https://github.com/chiragH717/devnira-core . Re-check fresh main HEAD, open PRs and Actions as this snapshot will age.

## Approved fixed economics
DEVNIRA / DVN, independent GPU-mined QPoW/Poseidon2 Layer-1, 12-second target, **8 decimals** (one DVN = 100,000,000 base units), SS58 prefix 190.
Max supply 100,000,000 DVN (10,000,000,000,000,000 units).
**90M DVN mined**, **10M company allocation** from real genesis to ONE verified company-controlled public wallet: **3M instantly liquid**, **7M on-chain locked with 12 Gregorian month cliffs**. First 11 unlock 583,333.33333333 DVN each; final 583,333.33333337 DVN. Initial subsidy 5 DVN/block, decrease 0.25% every 50,000 blocks, 90M miner emission cap. Fees are never new token issuance. Company public address and approved future UTC genesis timestamp NOT YET PROVIDED. NEVER invent test beneficiaries, private keys or real genesis hashes.

## Original branding lock
The original user-provided 13.zip + DESIGN_LOCK.txt contain FINAL transparent DEVNIRA GOLD/BLUE coin PNG, 3D coin, and GOLD/BLUE website source. **Never recolor, redraw, replace, recompress, change CSS/fonts/layout or substitute a generic D coin**. Brand palette #080d17 background, #111a2a panel, #28354b border, #eef3ff foreground, #9ba9bf muted, #f6bd60 gold, #55b7ff blue. Old original website copy (100% mining/zero premine) is OUTDATED and false for approved 90M/10M economics: do NOT deploy stale copy without separate approval. Current GitHub website is separate cyan/navy development source and not the final protected original. Domain devnira.co purchased via Hostinger, hosting not yet purchased/deployed or verified.

## Verified code and CI milestones — NOT active production
- PR #11: real Plonky2 4-ary depth 1/2 native amount/Merkle proof research, 15 public inputs, negative proof tests.
  https://github.com/chiragH717/devnira-core/pull/11
- PR #12: separately identified 8-decimal DVN native and embedded WASM runtime build with user sends DISABLED, 4.3.0/12-decimal V1 proof pallets still present.
  https://github.com/chiragH717/devnira-core/pull/12
  https://github.com/chiragH717/devnira-core/actions/runs/38690345552
- PR #13: non-dispatchable real FRAME Wormhole 22-PI on-chain historical block / UsedNullifiers replay and amount preflight, actual Rust pallet tests, NO mint/transfer.
  https://github.com/chiragH717/devnira-core/pull/13
  https://github.com/chiragH717/devnira-core/actions/runs/38697349201
- PR #14: 22-felt canonical layout and native value proof candidate. This layout ONLY does not authenticate the spend.
  https://github.com/chiragH717/devnira-core/pull/14
- PR #15: independently approved Ed25519 signed-release evidence gate and SHA256 report validation. No real auditor trusted yet; production remains fail-closed.
  https://github.com/chiragH717/devnira-core/pull/15
- PR #16: single combined inert 8-decimal runtime native/WASM build with 90M mining cap, 7M vesting mock and V2 on-chain preflight tests. User Send disabled.
  https://github.com/chiragH717/devnira-core/pull/16
- PR #17: **two actual localhost Substrate process** P2P connectivity, genesis and finalized history test PASS. No GPU mining, public peers or mined blocks verified.
  https://github.com/chiragH717/devnira-core/pull/17
- PR #18: durable finalized-block SQLite raw extrinsic indexer and opt-in loopback API. No decoded transfers/address balances, live RPC or public explorer.
  https://github.com/chiragH717/devnira-core/pull/18
- PR #19: first **single real Plonky2 22-PI research proof** cryptographically binding the same private spend secret, unspendable deposit account, 4-ary one-level Merkle membership, nullifier and full canonical header preimage and exact 8-decimal conservation. Real Rust proof/forgery tests GREEN. Still NOT active on-chain or recursive.
  https://github.com/chiragH717/devnira-core/pull/19
  https://github.com/chiragH717/devnira-core/actions/runs/38728156086
- PR #20: the very same test-only 22-PI authenticated leaf now also proves **exact floor(input * 4 / 10000) native fee**, with quotient/remainder and Goldilocks safe bounds (no modular wrapping), plus rounding and invalid fee tests. Rust proving + reference CI GREEN. Rate 4 bps is FIXED for research and NOT full FRAME fee governance.
  https://github.com/chiragH717/devnira-core/pull/20
  https://github.com/chiragH717/devnira-core/actions/runs/38728584822
- Windows: native Dilithium87 offline CLI + setup GUI build, unsigned and development-only. NOT secure audited live signed Send/Receive wallet.
- No Android app; GPU source candidates only (no actual Nvidia/AMD GPU work verified); pool offline share ledger; explorer now supports REAL local persisted **raw finalized SQLite blocks** with hash/parent chain integrity, but no decoded wallet addresses. Public RPC, website production hosting and external security audit absent.

## Production blockers — ALL REQUIRED
1. Extend the **successfully proved one-level 22-PI secret/nullifier/Merkle/header research** into full 4-ary depth, production dynamic fee-rate rules and public header-root authentication against a real historical DVN on-chain block. Current test-only script is NOT a production verifier.
2. Pinned full private/public recursive prover/aggregator and actual compatible on-chain V2 verifier keys/artifacts; active V1 4.3.0 proof path removed safely.
3. Atomic valid V2 settlement, persisted UsedNullifiers before mint, bounded issuance and exact miner rewards, invalid/replay/root/proof tests.
4. Actual independently launched 8-decimal spendable native/WASM runtime with real transfer signing. Current 8-decimal build is intentionally inert.
5. Genuine company-owned SS58-190 PUBLIC address + signed ownership proof and approved genesis time; exactly 3M liquid + 7M vesting and 90M mining; resolve vesting-pot existential-deposit conflict without minting extra coins; prove real genesis state/hash and network independence.
6. Audited Windows/Android encrypted/local custody, recovery and signed nonce/fee/SCALE extrinsics; verified production artifacts.
7. Two independent live nodes, real NVIDIA CUDA and AMD Vulkan/wgpu QPoW GPU mining, block rewards, restart/reorg/invalid tests.
8. Consensus-valid production pool with real shares/payouts; indexed finalized block/account/transaction explorer and reorg handling.
9. Hostinger hosting with user-authorized DNS/TLS and final original Gold/Blue site; secured public RPC/bootnodes, backups, monitoring, whitepaper/legal/support and signed wallet downloads.
10. Independent cryptographic, economic, wallet, consensus and infrastructure audit; production release gate green only with real attested evidence.

## Critical compatibility and ownership constraints
Pinned chain 482c5b9e02bec0adc70797eade0a67f60baf2619; circuits fa5f57dc1a1b755ff1b7f4fdb4309e1e06669ba2; miner c7838cbc86f7d74477da1771139f377a8e438072; Rust 1.93.0.
Quantus V1 leaf/wormhole quantizes native amounts using 10^10 for 12 decimals, with 4.3.0 proof crates. No simple 8-decimal rebranding can create a compatible proof chain. Earlier opt-in Merkle proof has 15 public felts, earlier inner amount proof 7, but real pinned wormhole V2 leaf PI ABI is 22. A 22-felt **shape** is NOT proof of sender authority, accepted historical Merkle root, domain identity or on-chain settlement. Root authentication requires proof of membership tied to header's trusted root, not an arbitrary supplied block hash.

A genesis-input JSON proposal is NOT a real genesis; config/genesis-proposal.json intentionally keeps public company address and genesis_timestamp_ms null. Sovereign vesting pot existential-deposit funding is a concrete blocker. scripts/release_evidence_gate.py originally received boolean data but PR #15 additionally requires external Ed25519 signatures and SHA256 launch-report evidence; the approved auditor list remains intentionally empty, so production is still blocked. Signed claims do NOT replace an actual independent audit. Previous ~32% is subjective and OUTDATED, do not claim an accurate new percentage.

## Execution sequence / user input needed
First complete cryptographically authenticated 22-felt V2 leaf + private/public recursive VK compatible with FRAME. Then active verifier, atomic payout and 8-decimal signed testnet. Then company-owned audited custody address and real 3M+7M genesis, real two-peer GPU mining and wallet; finally pool, explorer, public hosting, independent audit and signed launch. Owner later supplies ONLY verified PUBLIC DVN address plus signed public ownership proof, approves UTC genesis date, and authorizes hosting resources. **Never request or accept seed phrase, recovery words, passwords or private keys.**
