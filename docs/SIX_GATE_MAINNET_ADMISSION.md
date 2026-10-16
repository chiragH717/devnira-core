# DEVNIRA: unified six-gate launch admission — NOT MAINNET

This produces **one report** for all six remaining release streams, without relabeling GREEN research tests as a production blockchain.

Run locally:

    python3 scripts/six_gate_release_snapshot.py --revision "$(git rev-parse HEAD)" --json-out dvn-six-gate-status.json --markdown-out dvn-six-gate-status.md

To make an attempted production build fail when signed production evidence is absent:

    python3 scripts/six_gate_release_snapshot.py --revision "$(git rev-parse HEAD)" --require-evidence

The dedicated GitHub workflow uploads one summary artifact. **GREEN means that the safety report ran**, never that mainnet is ready.

## All six required work streams

1. Finalized authenticated V2 header-root history, valid historical witnesses and reorg rejection.
2. Approved domain-bound V2 verifier keys, private/public recursive proofs, real custody-backed atomic withdrawal/nullifiers, matching native + WASM.
3. Spendable independent 8-decimal native/WASM two-node testnet, signed transactions, QPoW rewards, 90M mining budget and reorg recovery.
4. Verified company-controlled SS58-190 **public** treasury identity and signed ownership challenge, approved UTC Genesis time, 3M liquid, 7M locked twelve Gregorian monthly cliffs, 90M unminted mining budget, no foreign prefunds.
5. Windows and Android secure signed Send/Receive/recovery and real NVIDIA CUDA + AMD Vulkan GPU PoW blocks.
6. Consensus-verified pool payouts, decoded public explorer, secured RPC, live devnira.co DNS/TLS, original approved Gold/Blue website assets, independently audited and signed release artifacts.

## External approval and evidence

The older production evidence protocol has nine product groups and Ed25519 independent auditor approval. The six-gate audit maps **every existing required field exactly once** into the six requested streams. It adds thirteen individually SHA256-pinned acceptance reports carried in the signed manifest's critical_acceptance_evidence property, including header finality, replay tests, actual hardware and public deployment. All signing must use a human-approved external auditor key in the protected repository. Missing or changed evidence, mismatched SHA or missing auditor key blocks admission.

This report does not create keys, grant money, publish wallets, deploy mainnet, modify DNS or enable Send. Even when all externally signed reports are admitted, an independent human release authorization and real live-chain security testing are still required.

## User-required external inputs

- A company treasury public SS58-190 address derived offline and its independently verified signed ownership challenge. **Never share private keys, seed phrases or recovery words.**
- A concrete approved future UTC Genesis time.
- Real independent security auditors and approved public signing keys, physically tested NVIDIA and AMD mining nodes, and authorized public hosting/infrastructure.

Until those exist, an exact mainnet launch date cannot be promised.
