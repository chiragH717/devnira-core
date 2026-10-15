# Stage 2: V2 leaf 22-public-input on-chain preflight

The canonical pinned wormhole leaf ABI is **22 Goldilocks felts**, not the
15-felt Merkle research prototype. Field positions are verified at build
time against the actual pinned qp-zk-circuits input source.

This change compiles a non-dispatchable function in the actual pinned FRAME
wormhole pallet and tests it against real mock-chain storage. It rejects
noncanonical fields, input/output inflation, non-native assets, fee-rate
drift, empty recipients, used/zero nullifiers, absent historical chain
block hashes and changed block identities. A valid preflight neither
writes a nullifier nor mints, burns or transfers any units.

**This is NOT a proof verifier**: a caller can invent 22 field values.
Proof soundness requires complete V2 leaf ownership and authenticated Merkle
root membership; recursive private/public batch proof versions and keys
must match exactly, and the verified V2 leaf must conform to this 22-felt
ABI. After proof verification, a future on-chain settlement must update
used-nullifier storage atomically with payouts and enforce correct roots,
fee rules, limits, mint/burn and historical block identity.

The present 15-felt candidate cannot be promoted as-is. The existing
4.3.0 on-chain V1 prover/verifier/settlement path has not been replaced.
The previously green 8-decimal node remains an inert research node with
all user Send operations disabled. The independently owned 10M company
public account and true DVN genesis remain unavailable. This change has
not altered the user's gold/blue logo or website design.
