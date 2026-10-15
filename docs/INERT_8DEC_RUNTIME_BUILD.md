# Stage 2: isolated DEVNIRA 8-decimal FRAME/WASM research build

This is a **build verification exercise**, not a usable cryptocurrency.
DEVNIRA's `UNIT=100000000`, 100M supply constant, SS58 prefix 190,
8-decimal DVN chain metadata and unique runtime spec name are compiled
into a pinned native Substrate node and matching embedded WASM. In order
not to activate 8-decimal balances against live 4.3.0 Quantus V1 proofs,
FRAME's BaseCallFilter is an allowlist of System and Timestamp only.
**EVERY wallet transfer, ZK withdrawal and vesting/user call is rejected.**

The CLI is separately patched to refuse Quantus public mainnet, Planck,
Heisenberg and arbitrary chain spec imports. Only isolated local research
`--chain dev` is permitted; source preserves the genesis *test accounts*
of Quantus development, so the chain is NOT an independently approved
production genesis and the source must NOT be distributed as a functioning
currency or miner. Even non-dispatchable runtime hooks may still use V1
bookkeeping; do NOT give development tokens economic value.

This is intentionally a *different* non-production path from
`scripts/patch_dvn_runtime_units.py`, which correctly refuses LIVE
8-decimal V2 activation while V1 4.3.0 settlement is linked. Never relax
that production gate because this isolated build compiles.

To complete the real Stage 2, a coordinated compatible V2 prover,
private/public aggregators, pinned on-chain verifier, historical root
membership, sender authorization, used-nullifier anti-replay, genuine
company-owned treasury, immutable 3M/7M issuance, 90M miner accounting,
matching native/WASM verified genesis and adversarial two-node tests are
required. All remain independently auditable gates.

## Red 8-decimal CI build diagnosis and repair

The initial full Rust native/WASM build failed with `error[E0080]` in the **inherited Quantus 21M-QTC mainnet vesting module**. That module had historical 12-decimal/21M allocation constants, but its assertion evaluated the *new* 8-decimal/100M DEVNIRA runtime constants. This patch isolates those **unreachable Quantus mainnet-only values** to the original 21M / 10^12 base unit inside the legacy preset and **retains every original invariant**; the CLI remains hard-blocked from loading inherited Quantus live chain specs. No Quantus premine, 27% allocation or old beneficiaries may be used for a DVN genesis. This repair is only for compiling the non-transacting research node; a genuine 10M company / 90M mining independent Genesis still must be implemented and audited.
