# DVN Genesis Vesting — concrete implementation handoff

## Code implemented
- `spec/genesis_manifest.py` constructs a deterministic, reviewable **off-chain** allocation manifest. For each beneficiary, its locked amount is divided into 11 equal integer-base-unit instalments plus a final remainder at exact Gregorian calendar-month boundaries.
- `scripts/create_genesis_manifest.py` accepts only *public* beneficiary addresses, timezone-aware genesis date and exact integer base-unit allocations, and writes JSON.
- `tests/test_genesis_manifest.py` checks February month truncation, totals, deterministic order, absent beneficiary validation and the upstream 64-schedule limit.

## Non-negotiable runtime requirements
Quantus `pallet-vesting` supports a cliff equal to the vesting end, which can enforce discrete month-end lump releases after integration into an actual genesis preset. The manifest is not currently wired into genesis, and payout safety, privilege restrictions and quantum alignment still need tests. At 12 schedules per beneficiary, the current 64 schedule bound supports at most five fully-vested beneficiaries without modifications. Before mainnet, beneficiary public keys and per-beneficiary allocation amounts must be explicitly approved and verified: do not invent addresses.

The on-chain vesting pot's existential deposit and possible genesis treasury/governance endowments must not silently add tokens beyond the **10,000,000 DVN** founding allocation. Verify the entire genesis issuance, not only beneficiary transfers. Audit emergency admin controls such as early schedule termination and retargeting to ensure the public vesting promise is enforceable.

## Example
```bash
python3 scripts/create_genesis_manifest.py \
  --beneficiaries beneficiary-public-allocations.json \
  --genesis-utc 2027-01-31T12:00:00+00:00 \
  --output devnira-allocation-proposal.json
```
The sample date is illustrative, NOT the launch timestamp. Input is deliberately not shipped with fake beneficiaries.

## Status and release
This is **not** a real Substrate genesis, spendable coin issuance, signing wallet, ZK circuit upgrade or full DVN node. The production safety gate must still fail while those modules are not integrated and tested.

## Updated engineering finding — reuse existing FRAME vesting pallet

Inspection of upstream `pallets/vesting/src/lib.rs` confirms `vested_amount` returns **zero while `now < cliff`**, and returns **the full grant when `now >= end`**. Since the schedule permits `start < end` and `start <= cliff <= end`, choosing `start=genesis_timestamp` and **`cliff=end=the Gregorian month unlock timestamp`** implements discrete monthly lump unlocks *without writing a new pallet*.

`spec/genesis_manifest.py` now emits `runtime_vesting_schedules_absolute_ms` tuples `[public_address, start_ms, cliff_ms, end_ms, amount_units]` and `anchor_to_first_timestamp=false`, ready to be fed into a future custom genesis preset after validation.

**Important blockers remain:** 12 grants per account count toward the upstream 64-schedule maximum, payout amounts must satisfy the ZK leaf quantum, addresses need SS58 decoding/format checks, genesis has to construct the vesting pot and verify *total* issuance, and existing treasury admin can terminate/retarget grants. To make the 12-month promise genuinely immutable, privilege restrictions and on-chain integration tests are required. The current JSON manifest is not on-chain.
