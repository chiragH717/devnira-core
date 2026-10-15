# DEVNIRA Stage 2 / V2 variable-depth Merkle proof test milestone

The opt-in V2 Plonky2 candidate now contains a private-depth, multiple-level
4-ary sorted Poseidon2 Merkle-path circuit, not only a single-parent example.
The tests prove valid depth-one and depth-two paths and reject incorrect
root/sibling/position, zero/changed network, false nullifier and inflated
native payout. All values are exact 8-decimal base units.

This is one **completed cryptographic development test**, not completed
Stage 2. The code supports allocating up to the upstream MAX_DEPTH but
tests depth one and two only; full-depth performance and formal security
review remain required. A public root supplied by the prover remains
UNAUTHENTICATED until on-chain historical-root storage checks it. A
client-chosen chain tag is not an actual independently pinned genesis.

Active V2 leaf ownership authorization, permanent on-chain nullifiers,
recursive batch integration with the production 22-felt layout, upgraded
prover/verifier (4.3.0 vs 4.4.0), independently built 8-decimal FRAME/WASM
runtime and real company-controlled genesis are not yet finished.

Do not activate the V1 wormhole under 8-decimal DVN; V1 truncates by 10^10
and uses u32 amounts. No address, supply or network launch is invented.
