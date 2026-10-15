# DEVNIRA production mainnet — independent signed evidence requirement

No full DVN mainnet release has been authorized or deployed. The native/WASM
8-decimal dev node deliberately disables user payments; ZK V2 is opt-in
only; there is no verified independent 10M company Genesis or 90M mining
network, no signed Windows/Android wallets, two real GPU node tests, production
pool/explorer/RPC, Hostinger TLS website or external audit.

`config/release-evidence.json` remains ABSENT. A user-provided JSON with
checkboxes set to `true` does not create launch authority.

The release workflow now **also** requires an independently approved
Ed25519 auditor signature on a canonical JSON manifest that includes an exact
40-character Git commit, real 32-byte genesis identity, one referenced
SHA-256 report per required launch gate, and path-safe on-disk evidence under
`evidence/production/`. Each report digest is validated. Invalid signed
payloads, symlinks/traversal and unapproved public signer keys are rejected.

`config/trusted-release-auditors.json` is intentionally an EMPTY allowlist:
until an actual independent reviewer has been engaged and their public key
verified and checked into a protected `main` branch by a human, even a
well-formed or self-signed manifest cannot pass. Cryptographic signature
verifies the REVIEWER'S ATTESTATION, not mathematical proof of actual blockchain
security. The reviewer must independently validate real-node test reports,
signed binaries, chain/genesis hash, hardware and infrastructure. This is a
*necessary* approval step, never a substitute for the entire audit.

Tests use ephemeral local private keys only under temporary directories;
they are never included in repository artifacts. No wallet or company treasury
private key is ever needed for this release process. The user-approved original
transparent Gold/Blue coin logo and website design remain untouched.
