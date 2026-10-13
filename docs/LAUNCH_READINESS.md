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
Provide beneficiary **public** addresses and allocation split for the 10M DVN allocation. Never provide seed phrases or private keys.

## Confirmed upstream amount-encoding blocker (2026-10-13)
The upstream runtime uses `UNIT=1_000_000_000_000` (12 decimal places) and the upstream ZK leaf encoding uses `AMOUNT_SCALE_DOWN_FACTOR=10_000_000_000`. The approved DVN unit is `100_000_000` (8 decimals). The current patched development candidate only changes chain-spec *display* decimals, not the runtime or ZK circuit encoding. That candidate is **NOT economically compatible** with 8-decimal DVN.

Run `python3 scripts/audit_amount_encoding.py upstream` as a **fail-closed** gate before calling any compiled candidate a DVN production runtime. The current Quantus baseline is expected to fail. Removing this check is not a fix: runtime unit, proof circuits, fee constants, address and ledger accounting must be migrated and tested consistently. Current wallet UI is read-only and cannot receive, custody or transfer funds.

## ZK amount width and vesting design findings (2026-10-13)
- The existing ZK leaf commits an amount quantized to a **u32**. Making the quantum `1` base unit preserves all 8 DVN decimals, but then a leaf can represent at most `4,294,967,295` base units (= `42.94967295 DVN`) without overflow. Changing the quantum only, or widening runtime balances only, **does not fix** proof circuit field widths and withdrawal verification.
- At a `10_000_000_000`-unit quantum (upstream), fractional DVN and exact monthly installments cannot be represented. A 1,000,000-unit quantum still loses the last six decimal digits.
- The existing Quantus vesting pallet uses **linear accrual between start and end** with a cliff. DVN requires **12 calendar-month cliff unlocks**, not a single linear schedule. A possible design uses 12 separate grants per beneficiary with full unlock at each month's cliff, but each grant must respect ZK payout granularity and the pallet's `MAX_GENESIS_SCHEDULES=64` bound. This is **not implemented** in consensus yet.
- `spec/zk_compatibility.py` and tests verify the precision/range contradiction. The production solution requires a cross-layer change to ZK amount representation, all corresponding proofs/verifiers, mining reward payouts and vested grants. Do not remove the production gate to suppress this finding.
