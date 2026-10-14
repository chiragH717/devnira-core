# DEVNIRA Stage 2: one-batch source audit and genesis-input tooling

This change tests the pinned **actual** Quantus chain sources instead of treating
opt-in Plonky2 test modules as active consensus. It does **NOT** finish the
Stage 2, activate V2 or create spendable DVN.

- `scripts/stage2_activation_audit.py upstream --expect-blocked` identifies
  proof crate 4.3.0 -> 4.4.0 skew, active V1 leaf quantization, active
  wormhole parser/verifier absence, runtime unit and 90M mining cap,
  genesis payout/funding and missing real company address/timestamp.
- `spec/genesis_candidate.construct_inputs` validates real SS58-190 **public**
  company address syntax, exact approved 3M unlocked + 7M sovereign vesting pot,
  12 Gregorian month cliffs and 90M **not pre-minted**. It refuses zero/missing
  address/timestamp and foreign/excess genesis accounts. The JSON is explicitly
  marked `runnable_chain_spec=false` and `production_genesis=false`.
- `scripts/build_genesis_inputs.py --output /path/to/inputs.json` works ONLY
  once `config/genesis-proposal.json` has the real approved public address
  and authorized UTC timestamp. Do not put recovery phrases/private keys in
  GitHub or chat. A well-formed SS58 public address alone does not prove
  signing ownership.
- `.github/workflows/stage2-activation-audit.yml` compiles/tests the
  Python source and audits actual pinned chain code. Its expected BLOCKED
  result is an **honest green safety check**, not a green mainnet.
- The existing production release gate stays fail-closed.

## Unimplemented proof-critical tasks

An opt-in 7-PI Poseidon2 conserved-value leaf proof cannot replace the active
22-felt root/nullifier/withdrawal protocol. Production requires an *entire*
verified V2 leaf (Merkle membership, sender authorization, nullifier and
domain separation), private batch, public batch, canonical public input
decoder, on-chain constant pinned verifier keys/artifacts, anti-replay,
receipt/reorg/settlement tests and exact fees. It needs a coordinated native
+ WASM runtime 8-decimal build and true independent genesis. Changing
`UNIT` by itself makes legacy 4.3.0 proofs unsafe.

## Real world dependencies

A company-controlled signing **public** address verified by an ownership
challenge and a finalized launch UTC timestamp are unavailable. Without them
a production genesis cannot be assembled. The two-node GPU testnet,
hardware NVIDIA/AMD mining, security review and product deployment remain
separate mandatory gates.
