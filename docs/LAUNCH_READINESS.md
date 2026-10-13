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
