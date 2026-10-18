# DEVNIRA Stage 2 — proof-authenticated atomic escrow settlement (test-only)

Status: **CI CANDIDATE — NEVER MAINNET, never distributable as a signed wallet**.

## Connected functional test path

1. Native pinned Plonky2 proves genuine depth-16 Merkle leaves and exports real serialized **24PI/46PI recursive proof bytes**; the two leaf witnesses share an authenticated historical root.
2. The actual pinned FRAME `pallet-wormhole` calls `qp-plonky2-verifier` to cryptographically validate the bytes, checks canonical serialization, parses fixed public PI positions, checks exact fee/payout sums, actual FRAME `BlockHash` test state and `UsedNullifiers` storage.
3. A **pre-funded development escrow** pays the two public recipients and the fee receiver through actual FRAME `T::Currency::transfer` (no mint/issue). Spent nullifiers and transfers are in one `with_transaction` boundary: any insufficient-funds/invalid proof/history/replay error rejects the entire batch. Native unit tests compare balances, total issuance, used-nullifier flags and no-partial-payout rollback.

## Explicit exclusions

- Function is **`#[cfg(test)]`** and cannot be called from production runtime/WASM or a user extrinsic. The runtime remains intentionally **NO SEND**.
- Verifier keys are publicly exported **development** key material, not audit-approved runtime-pinned VKs. Production should never accept verifier data provided with a proof.
- `BlockHash` is explicitly mocked to equal a proved test header, not independently verified finalized DEVNIRA history.
- Escrow is pre-funded using test-only genesis endowments, not linked to real proof-authorized deposits. A real proof **alone** does not establish any actual on-chain locked funds in an independent chain.
- The current pinned Quantus V1 deposit/wormhole tree retains 12-decimal and `10^10` quantum semantics; no production-compatible 8-decimal deposit authorizer / ZK-tree bridge is active.
- No live private/public batch production aggregator, no production atomic settlement dispatchable, no audited beneficiary funding, no treasury genesis, no working Windows/Android signing wallet, no GPU pool or 2-node mining.

**Next engineering boundary:** develop independent 8-decimal deposit-backed commitment and tree, pin independently reviewed V2 proving/verifier keys in a consensus-safe pallet, ship bounded/weighted and replay-safe dispatchable settlement with a true finalized historical root, then signed spendable local testnet and 10M company genesis using only independently supplied audited public wallet addresses.

All Gold/Blue original website/logo/coin assets are not modified by this work.
