# DEVNIRA staged batch — final tests deferred

This is one code staging batch, not a production launch. Previously completed PR #29–39 are NOT rerun. The new changes will be tested together in the explicitly requested final acceptance phase.

## Four real code additions
1. scripts/dvn_unsigned_dev_signing_intent.py — two independently synchronized finalized DEV peers must agree on genesis, spec/tx versions, metadata hash, sender nonce, account balances, supply, 8-decimal DVN and SS58-190 identity before an unsigned, SHA256-pinned DEV signing intent can be emitted. No keys, secrets, signature, or transaction submission.
2. scripts/dvn_v2_consensus_root_probe.py — validates actual System.DvnV2HeaderMode, Wormhole.DvnV2TreeRoot and Count, per-height history storage, and qp_header.zkTreeRoot on two finalized peers. Derives FRAME Twox128 and Twox64Concat keys and refuses missing/inactive V2 roots. The existing DEV chain has V2 mode disabled; therefore this must intentionally fail until an approved runtime activates an independently genuine V2 domain. NOT a proof verifier or atomic settlement.
3. scripts/dvn_physical_gpu_probe.py — requires actual Linux physical DRM vendor and kernel-driver presence for NVIDIA or AMD; rejects CPU fallback. This is NOT cryptographic PoW work, solved shares, mining reward, or real pool evidence.
4. services/finalized_indexer.py — optional --confirm-rpc checks every indexed block hash, complete finalized header including the zk root, extrinsic body and revalidates both independent peers before SQLite atomic commit. Does not decode transfers or expose a production explorer.

## One final test later
The staged test cases in tests/test_final_batch_new_boundaries.py are intentionally not executed in this batch. Run python3 -m scripts.dvn_last_acceptance with no flags to display external prerequisites; explicit --run is required for final execution. That run checks signed DEV transaction evidence, V2 authenticated root provenance, actual hardware presence and cryptographically signed release admission. It will not give an unearned green result when independent network/VK/hardware/treasury information is absent. Do not auto-run the older 22PI to 24PI to 50PI proof suite again.

## What cannot be declared finished
- A real independently signed DEV-only Dilithium SCALE transfer finalized on both peers with exact balance, nonce, fee, unchanged issuance and replay rejection.
- Audited production PRIVATE/PUBLIC fixed verifier keys; active native AND WASM prover/verifier, deposit-backed atomic payout, historical witnessed V2 root and replay-safe nullifiers. Existing verifier/escrow code is development cfg(test), not live.
- Actual treasury ownership, independently built 8-decimal genesis with 3M immediately liquid and 7M locked in twelve calendar cliffs, 90M miner-only budget.
- Genuine hardware QPoW mining, chain accepted work, pool shares/rewards, NVIDIA CUDA and AMD Vulkan performance, external hardware evidence.
- Global signed Windows/Android wallets, public website, explorer/RPC TLS and deployment, external security audit and explicit production authorization.

No mainnet tokens, secret keys, production send, public infrastructure, DNS or company Genesis are modified by this PR. Final success requires external approvals and live evidence, not a green code-only check.
