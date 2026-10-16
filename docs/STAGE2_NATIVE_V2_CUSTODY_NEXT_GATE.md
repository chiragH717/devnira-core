# DVN Stage 2: internal native custody ledger (NO SEND)

The immutable pinned chain receives a non-dispatchable FRAME pallet extension; it is not a production wallet deposit call or an active private settlement.

Native balances are transferred into a deterministic vault before any exact 8-decimal credit receipt is written. The FRAME storage transaction rolls back both balances and receipts on any failure. A dedicated receipt sequence and canonical recipient transfer counter reject overflow; the outstanding sum must remain <= 100,000,000 DVN in base units. No minting. Incoming vault transfers are excluded from the 12-decimal V1 recorder rather than entering false V1 Merkle leaves.

Real Rust FRAME tests on the pinned original wormhole pallet cover amounts of 1 and 2 smallest base units, recipient counts, recorded receipts, vault/source balances, zero and oversupply, noncanonical Goldilocks alias, vault self-funding, insufficient funds, count overflow, issuance invariance and V1 leaf rejection. Python tests only check patch anchors; they do not substitute for the native Rust run.

Still missing: signed deposit extrinsic, real 8-decimal Poseidon2 commitment tree/witness, finalized independent block header history, audited/fixed V2 verifier key in consensus, production atomic nullifiers/fees/withdrawal, same native and WASM execution, independent funded 10M treasury genesis and public GPU-mined network. Do not enable user Send, merge production flags or deploy mainnet based on this component.
