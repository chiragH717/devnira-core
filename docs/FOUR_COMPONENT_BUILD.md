# DEVNIRA — One workflow for the four remaining components

Run manually: [four-component-build.yml](../.github/workflows/four-component-build.yml).

The workflow evaluates the four tracks **in parallel**, records the actual development build outcomes, and then always runs a **fail-closed production gate**. Its red release-gate job is intentional as long as evidence is missing. **Do not change the release gate to green by substituting mock evidence.**

| Track | What this workflow really verifies | What is STILL required before launch |
| --- | --- | --- |
| Active ZK circuit/prover/verifier | Compiles V2 amount prototype in upstream `qp-wormhole-inputs` | V2 Poseidon2 leaf, prover, verifier, aggregation, real valid/invalid withdrawal proofs |
| DVN runtime + genesis | Compiles patched rewards/vesting in upstream 12-decimal node and WASM | Fully migrated 8-decimal runtime, enforced 100M total supply, independent genesis funded using approved public beneficiary keys, fees and 3M liquid / 7M locked |
| Windows wallet | Packages a read-only local-RPC node monitor as an EXE | Secure audited keys, valid DVN address format, signed send/receive, reliable balances and vesting display |
| GPU mining testnet | Verifies QPoW reward formula reference | Real NVIDIA/AMD GPU miners, two-node sync, PoW validation, chain reorg and reward/cap tests |

The approved immutable economic targets: 100M DVN total, 90M mined, 10M founders/investors/team, 3M immediately accessible, 7M released in 12 **calendar-month** instalments. Node identity must be independent of Quantus. No wallet seed/private key is ever required in GitHub.

A **verified public wallet address and beneficiary split** are required inputs to create *real* genesis balances. No fake recipient addresses are used. The development node's existing genesis does NOT allocate actual DVN coins.

The current workflow is a **candidate integrator**, **not a complete one-command mainnet builder**. It is intentionally manual-only to avoid repeatedly consuming 30–60 minutes of CI on every small code commit. No workflow can establish NVIDIA/AMD hardware compatibility on a runner with neither GPU. No workflow can certify cryptographic security from arithmetic unit tests.

## Completion condition

The project is *not finished* until a pinned, reproducible 8-decimal DVN native+WASM runtime with a DVN-only independent genesis, matching Poseidon2 leaf/proof/verifier circuit, secure Windows signing wallet and multi-node actual GPU mining testnet have all passed recorded integration and adversarial tests. `scripts/release_evidence_gate.py` rejects missing individual evidence. Even when it passes, a separate security review is needed.
