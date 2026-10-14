# DEVNIRA company custody -> genesis and V2 Poseidon migration (engineering record)

## Approved economics (unchanged)

The treasury allocation belongs to **ONE company-owned DEVNIRA account**, not separate founder/investor addresses: 3,000,000 DVN immediately liquid, 7,000,000 DVN locked in 12 exact Gregorian monthly cliff installments, **90,000,000 DVN GPU PoW**, **100,000,000 DVN immutable total supply**, eight decimal places. Public company account address, genuine wallet custody, exact launch timestamp and independent genesis hash are still pending. Never place real mnemonic phrases, signing keys or company recovery material in GitHub Actions, chats, tickets or source.

## 1. Actual native Dilithium87 wallet source

`scripts/patch_dvn_wallet_cli.py` modifies the pinned upstream *Rust* node code in its key generator, CLI, crypto signing scheme, and runtime genesis SS58 display/validation:

- CLI is `key devnira` instead of the upstream `key quantus`.
- Isolated hardened derivation namespace: standard `m/44'/900190'/0'/0'/0'`, Wormhole `m/44'/900191'/0'/0'/0'`. These are DEVNIRA project-specific paths, not official registered SLIP-44 types; never present them as a published industry standard.
- Address prefix 190, consistent with `spec/ss58_company_account.py` and DEVNIRA runtime address prefix.
- Rust node now implements actual `key devnira-sign` and `key devnira-verify` for address-bound company ownership challenges. The default `sp_core::Pair::from_phrase` hardened path is also patched to match `key devnira`. Generic upstream `key sign`/`key verify` do **not** exist in this node.
- Newly generated secret phrases require both interactive stdin and stdout. Noninteractive build jobs must never generate fresh production secrets. Existing no-echo stdin mnemonic import is preserved.

`four-component-build.yml` recompiles the node and tests public mnemonic recovery, native signing/verification with the published **unsafe-for-custody** upstream test mnemonic, rejection of a tampered message, and refusal to create real wallet secrets on a noninteractive CI runner.

**Not yet a transaction wallet:** the offline custody-challenge signer is not a transaction signer. A Windows **public Receive + finalized Free/Reserved Balance read-only preview** now compiles, but Secure-at-rest key management, nonce/fee calculation, audited SCALE extrinsic signing/submission and **Send** remain unimplemented. See [FOUR_POINT_STATUS.md](FOUR_POINT_STATUS.md).

## 2. Link the company account to genesis without private keys

`spec/verify_company_custody.py` checks an address-bound, 256-bit random, 24-hour proof-of-control challenge that includes **DEVNIRA network identity, company address and expiry**. It delegates Dilithium87 signature AND the expected SS58-190 company address binding to the **SHA-256 pinned native `key devnira-verify` command**. No non-existent upstream `key inspect --public` command is called.

`scripts/prepare_company_genesis_custody.py` issues the public signing challenge and, only after successful proof verification, produces an OFF-CHAIN proposal for 3M instant + 7M locked / 12 exact monthly grants. Outputs intentionally contain neither private seeds nor signing passwords. It **does not** set `production_genesis: true` or generate a live node's genesis state.

Sample syntax (use ONLY on a secured machine after the independent binary has been built and audited; do **not** run with the published CI test mnemonic):

```text
devnira-node key devnira --scheme standard --wallet-index 0
python scripts/prepare_company_genesis_custody.py challenge --company-public-address <DVN_SS58_190_ADDRESS> --output company-public-challenge.json
```

The signer must sign exactly the `message` field using the local native Dilithium87 wallet; assemble a public certificate with `public_key_hex` and `signature_hex`. Then run `manifest` with that certificate, the trusted native binary's SHA-256 and a future UTC genesis timestamp. This must be done securely by the company at the **actual** launch stage. An address alone cannot establish company custody.

## 3. Actual 8-decimal Poseidon source candidates

`scripts/patch_zk_tree_native_v2.py` adds `hash_leaf_native_v2` to the **real FRAME ZK-tree** source, keeping the same Poseidon2 layout while committing native `u64` amounts exactly, without Quantus V1's 10^10 scale-down or u32 saturation. Above-100M-DVN native leaves are rejected. Real pallet tests check that a single 1e-8 DVN unit changes the commitment.

`scripts/patch_zk_leaf_amount_v2.py` adds an actual Plonky2 Poseidon2 leaf hash gadget constrained to the same eight-felt layout and 100M base-unit cap, with real positive/negative proof tests and one-base-unit hash sensitivity. This is installed in the upstream circuit crate; **it is still a candidate module, not part of the active leaf/prover/aggregator/verifier and runtime withdrawal verifier**.

`zk-tree-native-v2.yml` builds/tests the FRAME candidate; `zk-proof-input-v2.yml` builds/tests the Plonky2 proof candidate. `four-component-build.yml` includes the native crypto and V2 FRAME tests in its full node/WASM development candidate. Successful source builds do **not** authorize enabling 8-decimal native balances with the old production prover/verifier.

## 4. Remaining nonnegotiable production gates

- Activate **the same versioned V2 encoding** on chain, full leaf proof, prover, aggregator, verifier and fee/value-conservation rules (including malicious witness rejection and cross-layer golden hashes).
- Build an independent DEVNIRA-only eight-decimal runtime and genesis preset, with only 3M company liquid + 7M exact-pot balance, 12 immutable monthly schedules, **no Quantus/dev premine**, separately vetted governance, separate SS58, distinct genesis and full 90M mined-only reward budget.
- Build a Windows **transaction signing, receiving and sending** wallet with audited key custody, address ownership, RPC/chain pinning and signed transaction broadcast.
- Run two independently bootstrapped nodes with actual Nvidia and AMD QPoW GPU hardware, verify live rewards, balance and supply accounting, transfer proofs, invalid proofs, fork/reorg and failure recovery.
- Obtain verified development/production CI results and a security review before mainnet.

**Wallet native signing, Windows read-only EXE, Plonky2 V2 amount/source candidate tests and NVIDIA/AMD source typechecks have passed their respective development CI. Active V2 aggregator/verifier, independent 8-decimal mainnet runtime/genesis, actual Windows transaction sending and GPU hardware tests have NOT passed. See [FOUR_POINT_STATUS.md](FOUR_POINT_STATUS.md).**
