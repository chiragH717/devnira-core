# DEVNIRA FRAME genesis: exact 10M issuance, no extra vesting-pot ED

## Decision locked for company treasury

- 100,000,000 DVN total maximum, 8 decimals, 90,000,000 DVN minted by GPU PoW (never part of genesis initial balances).
- Single company-controlled DVN public beneficiary: **3,000,000 DVN liquid at genesis**, **7,000,000 DVN vesting**, released on 12 exact Gregorian calendar-month cliffs. First 11 payments: `58_333_333_333_333` base units each; final: `58_333_333_333_337`. No extra team/investor accounts.
- At genesis, the company public account must hold exactly `300_000_000_000_000` base units; the pallet's sovereign vesting pot must hold exactly `700_000_000_000_000` units. Total genesis issuance must be **exactly `1_000_000_000_000_000` units** (10M DVN) and no more.
- Company real signing address and finalized genesis timestamp **are missing**; never substitute a test key, seed, copied Quantus address or zero account. Company private keys are never required in source control.

## Root problem in upstream FRAME

Upstream `pallets/vesting/src/lib.rs` requires `sum(grants) + Currency::minimum_balance()` in the pot and always transfers with `Preservation::Preserve`; upstream `runtime/src/genesis_config_presets/mod.rs` endows the pot with this extra ED buffer. This creates a **strictly positive additional genesis issuance** when users require exactly 3M liquid and 7M locked.

## Implemented in `scripts/patch_exact_genesis_vesting.py`

1. Add `pallet_vesting::Config::ExactGenesisFunding: Get<bool>`. Default Quantus-development runtime uses `ConstBool<false>` and retains previous funding behavior.
2. With the flag true, pallet genesis asserts pot holds **exactly scheduled obligations** (no extra ED), and runtime genesis builder uses the same formula.
3. For claims from the pot in exact mode, use `Preservation::Expendable` to permit **the final 100% payout**, but first reject any transfer that leaves a **positive pot balance below existential deposit**. This prevents dust reaping while other obligations are pending.
4. Keep normal transfers, permissionless claims, original treasury checks and Wormhole/ZK proof recording; recorder failure must roll back a transfer.
5. `try_state` in exact mode checks outstanding obligations without adding an ED buffer.
6. Existing development and upstream runtime remain in their legacy mode until DVN has an active **matching 8-decimal ZK transfer proof system**. Do not enable `ExactGenesisFunding = true` alone without funding the pot according to that mode.

## Three real FRAME mock-runtime integration tests

- `dvn_exact_pot_all_twelve_monthly_grants_mint_no_extra_ed`: 7M DVN, all twelve Gregorian cliffs, **exact funds move** and `Balances::total_issuance()` never changes, final pot reaches zero.
- `dvn_exact_pot_prevents_premature_reaping_below_ed`: cannot claim in an order that would leave an under-ED dust pot, but lawful later ordering can complete both grants.
- `dvn_exact_pot_failed_zk_proof_does_not_move_or_mint_funds`: a failed ZK proof-recorder write rolls back the full transfer and leaves the claim retryable.

Tests are injected into the **actual upstream FRAME vesting pallet** using `scripts/test_exact_genesis_vesting.py`. They compile/run through `.github/workflows/exact-genesis-pot.yml`, `stage2-combined-runtime.yml`, and `four-component-build.yml`. Latest revisions pin upstream sources via `config/upstream-pins.json` rather than pulling a moving HEAD.

**Current verification boundary:** The new code and workflows have been committed. Their new CI compile and mock FRAME test results have **not yet been confirmed** in this conversation. Even passing these FRAME tests does not mean the 8-decimal DEVNIRA runtime or independent genesis exists.

## Before activating on actual DEVNIRA chain

- Implement and verify the full 8-decimal V2 Poseidon2 leaf / Wormhole transfer / prover / aggregator / verifier, including exact 1-base-unit proof conservation.
- Add a true DEVNIRA-only runtime preset with `ExactGenesisFunding = true`, its own SS58, chain-id/genesis state, **no upstream automatic dev balances or Quantus mainnet 27% allocation**, correct governance and QPoW, and only the company-approved public account and locked pot.
- Validate that an on-chain genesis company account balance is 3M DVN, pot balance 7M, exactly 12 permanent monthly cliffs, and total initial issuance exactly 10M; lock admin cancellation/retarget of founding grants.
- Verify independent 12-second block network with 90M miner-only subsidy cap, live signed transfers, two-node synchronization, actual NVIDIA **and** AMD mining, network reorg/fork and invalid-proof tests.
- Review the exact-pot survival semantics when other runtime features donate to or withdraw from the pot; audit for account liveness, fees, balance holds, storage migrations and potential governance upgrades.

**No blockchain/mainnet release is authorized by this document or by green reference checks alone.**
