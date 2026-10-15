# Stage 2 — 22-field V2 cryptographic layout candidate

This **opt-in** Plonky2 circuit verifies the canonical 22-felt layout
against the pinned qp-zk-circuits source. Exact 8-decimal native amount
conservation is constrained, and the circuit exposes committed output
amounts, fee-rate test constant, Poseidon2 nullifier, public claimed block
hash, block number and original native input. Genuine Rust proof and
negative tamper tests run in GitHub CI.

**NOT an active or authentic withdrawal proof.** A prover can choose
a private leaf and a public block hash: this candidate does NOT prove that
the leaf belongs to the real historical tree, that the private signing key
owns it, that fee policy is complete, or that nullifiers were recorded
atomically during settlement. No private/public recursive VK or on-chain
V2 parser is switched. The older Merkle research prototype has 15 public
felts, whereas this canonical field-layout test has 22. They do not form
one complete compatible active circuit yet.

A green proof test therefore must not authorize minting, Send/Receive or
a production genesis. The next work must cryptographically bind full-depth
private Merkle membership to an accepted historical root in its header,
complete owner authority and full recursive-batch verifier activation.
