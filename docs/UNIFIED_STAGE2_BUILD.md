# DEVNIRA unified Stage 2 native/WASM build — bounded milestone

This combines in the **SAME original pinned Rust FRAME source tree**
all of: (1) DEVNIRA 8-decimal/100M runtime constants, (2) 90M miner-only
subsidy reservation accounting + fee recycling, (3) 12 Gregorian month
immovable genesis grants + exact 7M DVN vesting pot source semantics and
mock FRAME tests, (4) on-chain read-only 22-public-input header
and nullifier state preflight tests, (5) DEVNIRA research chain ID/SS58-190
and an allowlist which **DENIES ALL USER TRANSACTIONS**.

GitHub CI compiles one native release executable and embedded WASM, runs
actual separate mining, vesting, and V2 mock-FRAME tests on that same
source tree, and checks the emitted local development chain spec. It does
not publish the unsafe developer executable or activate old QTC networks.
V1 4.3.0 proof crates remain compiled; user dispatch is blocked. The
actual independent genesis has no signed treasury owner, and V2 leaf
circuits are still unbound to on-chain trusted root and key authority.
A green build is evidence of source compatibility, not mainnet
readiness, GPU mining, secured wallet or audit.

Existing exact-pot production option is intentionally FALSE in inert
development runtime. Green mock tests of 7M pot do not prove a real DVN
genesis, nor should Quantus development accounts be rebranded as a
company treasury. An actual trusted company address, signed ownership,
V2 security/atomicity, full independent genesis and third-party review
are still launch blockers.

The user-approved original transparent gold/blue D coin and website
design are unchanged. Never publish the stale 100%-mined website wording
when approved economics are 90M mining / 10M treasury.
