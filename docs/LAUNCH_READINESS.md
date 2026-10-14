# DEVNIRA launch readiness — engineering gates

**Status: NOT MAINNET READY.** Do not advertise, distribute funds or launch using the upstream-runtime development candidate.

## Approved economics
- 100,000,000 DVN max, 8 decimals; 90,000,000 DVN mined; 3,000,000 DVN immediately available at genesis; 7,000,000 DVN unlocked in 12 monthly installments.
- 5 DVN initial mining subsidy; exact floor(500000000*(399/400)^epoch) base units every 50,000 blocks; 1-base-unit tail; issuance stops at 90M mined DVN.
- 12 second target; QPoW/Poseidon2.

## Mandatory before final build
1. Pin and import upstream code into reproducible source control (current CI clones moving HEAD).
2. Replace upstream mining reward formula in **actual pallet**, account for collected fees and pending payouts, and track minted-miner-only issuance in authenticated state. Do not infer mined issuance from total supply after fee burns.
3. Verify 8-decimal balance units against wormhole/ZK leaf quantum and all fees/deposits.
4. Implement genesis balances for beneficiary public addresses: 3M liquid and 7M on-chain locked, not just JSON documentation. Specify consensus-safe month-boundary timestamp behavior.
5. Establish a unique runtime identity, genesis state, address prefix and network isolation; verify all dev/Quantus prefunds are absent in the final chain spec.
6. Run unit/property tests, native/WASM compile, chain-spec generation, 2-node sync, mining and transfer/vesting tests, including at month boundaries and near cap.
7. Audit consensus, economics, upgrades and wallet compatibility. Verify NVIDIA/AMD miners on hardware.

## What has been demonstrated
A patched **upstream runtime development candidate** compiled and exposed RPC in previous GitHub Actions runs. This does not establish that DEVNIRA reward economics or vesting run on chain.

## Blockers requiring user action later
Allocation policy is **one company-controlled wallet** holding the entire 10M DVN founder allocation (3M available + 7M in 12 monthly grants). The verified independent DEVNIRA **public** address remains pending because the signing wallet and genesis are not finalized. Never provide seed phrases or private keys.

## Confirmed upstream amount-encoding blocker (2026-10-13)
The upstream runtime uses `UNIT=1_000_000_000_000` (12 decimal places) and the upstream ZK leaf encoding uses `AMOUNT_SCALE_DOWN_FACTOR=10_000_000_000`. The approved DVN unit is `100_000_000` (8 decimals). The current patched development candidate only changes chain-spec *display* decimals, not the runtime or ZK circuit encoding. That candidate is **NOT economically compatible** with 8-decimal DVN.

Run `python3 scripts/audit_amount_encoding.py upstream` as a **fail-closed** gate before calling any compiled candidate a DVN production runtime. The current Quantus baseline is expected to fail. Removing this check is not a fix: runtime unit, proof circuits, fee constants, address and ledger accounting must be migrated and tested consistently. Current wallet UI is read-only and cannot receive, custody or transfer funds.

## ZK amount width and vesting design findings (2026-10-13)
- The existing ZK leaf commits an amount quantized to a **u32**. Making the quantum `1` base unit preserves all 8 DVN decimals, but then a leaf can represent at most `4,294,967,295` base units (= `42.94967295 DVN`) without overflow. Changing the quantum only, or widening runtime balances only, **does not fix** proof circuit field widths and withdrawal verification.
- At a `10_000_000_000`-unit quantum (upstream), fractional DVN and exact monthly installments cannot be represented. A 1,000,000-unit quantum still loses the last six decimal digits.
- The existing Quantus vesting pallet uses **linear accrual between start and end** with a cliff. DVN requires **12 calendar-month cliff unlocks**, not a single linear schedule. A possible design uses 12 separate grants per beneficiary with full unlock at each month's cliff, but each grant must respect ZK payout granularity and the pallet's `MAX_GENESIS_SCHEDULES=64` bound. This is **not implemented** in consensus yet.
- `spec/zk_compatibility.py` and tests verify the precision/range contradiction. The production solution requires a cross-layer change to ZK amount representation, all corresponding proofs/verifiers, mining reward payouts and vested grants. Do not remove the production gate to suppress this finding.

## Runtime reward patch candidate (2026-10-13)
- `scripts/patch_reward_runtime.py` now modifies the **actual upstream FRAME mining rewards pallet** in a temporary Quantus checkout, rather than only modeling issuance in a separate reference crate. It introduces authenticated storage for minted miner subsidy and reserved unpaid miner subsidy. Transaction-fee recycling stays separate; the exact reward table comes from `scripts/generate_emission_table.py`.
- The independent compile gate is `.github/workflows/reward-pallet-build.yml`, automatically triggered on pushes to the patch/generator/workflow. It verifies deterministic epoch rewards and attempts native plus no_std WASM **pallet compilation**, not the full DEVNIRA chain.
- **Status: candidate, compilation results not yet verified.** This patch is not applied in `scripts/prepare_upstream.py` or the production build. Even a passing compile does not imply tested reward issuance; upstream mining-pallet unit tests target the original schedule and must be rewritten for DVN. A 90M cap requires integrated 8-decimal runtime and cross-pallet issuance checks.
- Full DVN ZK circuits, proof generation, wallet signing, consensus genesis and 12 monthly on-chain unlock enforcement are still pending. **Do not release funds or call this mainnet-ready.**

## Stage 2 genesis grant protection candidate — 2026-10-13
The latest submitted screenshot shows **DEVNIRA on-chain monthly vesting integration #4: green/success**. This validates the test-only Gregorian cliff behavior of the upstream vesting pallet, **not** funded DVN founder allocations.

The upstream vesting pallet permits treasury/root to `end_schedule` and `retarget_schedule` genesis grants, potentially defeating the advertised 7M-DVN founder lock. `scripts/protect_genesis_vesting.py` introduces an authenticated genesis-schedule count and rejects these two administrative actions on genesis grants. `scripts/test_genesis_vesting_protection.py` injects a FRAME test to verify before-cliff claims fail, administrator cancellation/retarget fail, and post-cliff payout succeeds. `stage2-genesis-vesting.yml` attempts automatic compile/test. **This is a development patch only; new CI outcome is not yet verified.** Existing upstream tests asserting cancellation/retarget of genesis schedules will need scope-appropriate reconciliation. Governance/runtime code upgrades still need security review.

Still missing for **Stage 2 completion**: end-to-end 8-decimal ZK field and proof migration (beyond reference encoder); DVN runtime UNIT, fees, rewards, vesting quantum and issuance tests; real mainnet genesis funded by beneficiary **public keys** and exact 3M/7M split with no accidental extra issuance; reproducible pinned upstream source; two-node sync and GPU mining tests; Windows signed wallet and full testnet verification. No production release should be represented as complete yet.

## Consolidated engineering review — 2026-10-14

The reviewed upstream source confirms that `runtime/src/genesis_config_presets/mod.rs::genesis_template` endows multiple development accounts and allocates **vesting totals plus existential deposit** to the pot. The upstream vesting pallet enforces `pot balance == obligations + minimum_balance` at genesis and pays using `Preservation::Preserve`. With a strict 3M company liquid / 7M claimable lock / 10M minted at genesis requirement, that design needs a separately reviewed consensus change; simply setting token display decimals to 8 or suppressing checks does not fix it.

The latest user-supplied verified green `four-component integration build #3` was a **development candidate**, not an active production V2 proof system or independent genesis. Its Windows artifact is a read-only node monitor and its GPU job runs reference/prerequisite tests without NVIDIA/AMD hardware. The active Poseidon2 leaf, matching aggregator/prover/verifier, production signing wallet, live two-node GPU mining and post-migration security review are outstanding.

To prevent recurring confusion, `scripts/project_status.py` generates a machine-readable single-project summary with the approved parameters and explicit blockers. `verify.yml` uploads `devnira-project-status.json` after unit tests. **The new pipeline's success has not yet been confirmed**, and even a green result is not a mainnet approval.
