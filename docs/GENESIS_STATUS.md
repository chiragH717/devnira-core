# DEVNIRA independent genesis proposal — NOT LIVE

Independent chain identifier: `devnira-mainnet-v1`. Name: DEVNIRA; symbol DVN. Proposed QPoW/Poseidon2 consensus; 12-second target; 100 million DVN hard cap, 10% (10 million DVN) founders/team/investors allocation and 90% (90 million DVN) GPU/PoW mining allocation; one company-controlled public beneficiary address pending but 3M/7M twelve-calendar-month vesting policy approved, initial balances currently empty; 5 DVN initial subsidy; 399/400 multiplier each 50,000 blocks.

`config/genesis-proposal.json` is a **planning document, not a Substrate chain-spec JSON**. It cannot launch a chain.

## Blocking engineering tasks

- Fork and pin actual Quantus upstream source with notices.
- Modify node chain spec, runtime constants, QPoW consensus and reward pallet.
- Produce real WASM runtime and genesis storage state root.
- Set unique network protocol identifiers, bootnodes, address prefix and real genesis hash.
- Build and run independent nodes, mine blocks, and verify network isolation.
- Implement and audit the 10 million DVN genesis allocation with approved beneficiary addresses, vesting/lock rules and transparent accounting; do not insert fabricated addresses.
- Cap miner rewards to the separate 90 million DVN mining allocation and validate total issuance never exceeds 100 million DVN.
- Cross-validate exact integer reward schedule over all epochs.
- Run integration and security tests before a public launch.

No real genesis block hash can be claimed until an actual runtime is built and genesis storage computed.

## Approved team/investor vesting policy (supersedes earlier two-year cliff)

- 3% of total supply (3,000,000 DVN): immediately unlocked at mainnet genesis.
- 7% of total supply (7,000,000 DVN): unlock in 12 equal monthly installments over one year, starting one calendar month after mainnet genesis.
- Base-unit rounding: first 11 monthly installments each release 583,333.33333333 DVN (58,333,333,333,333 base units); final month releases 583,333.33333337 DVN (58,333,333,333,337 base units). Total exactly 7,000,000 DVN.
- 90% (90,000,000 DVN): reserved for GPU/PoW mining.
- Implement enforceable on-chain vesting with calendar-month boundary semantics defined in consensus; no off-chain promises.
- Single company public beneficiary address and genesis timestamp pending. Allocation policy is approved; no coins distributed.

## New actual FRAME funding candidate (2026-10-14)

The upstream vesting pallet and runtime genesis builder originally require an extra existential-deposit buffer in addition to the full locked pot. [scripts/patch_exact_genesis_vesting.py](../scripts/patch_exact_genesis_vesting.py) introduces **opt-in** exact genesis funding to issue precisely 7M DVN to the pot with no extra premine while ensuring payout ordering cannot reap a nonempty below-ED pot. The final payout can transfer all remaining funds and eliminate the pot; proof recording remains mandatory. The old 12-decimal development runtime keeps legacy behavior by default.

[Three new FRAME tests](../scripts/test_exact_genesis_vesting.py) exercise all 12 month cliffs, exact `Balances::total_issuance()`, sub-ED protection and ZK proof rollback in mock runtime. [Dedicated CI](../.github/workflows/exact-genesis-pot.yml) and the combined runtime build compile/test this source against a [pinned Quantus revision](../config/upstream-pins.json). **New exact-pot CI results are unconfirmed**. This is **not** a live DEVNIRA genesis; the matching V2 proof system, independent runtime, company public address and hardware tests remain necessary.
