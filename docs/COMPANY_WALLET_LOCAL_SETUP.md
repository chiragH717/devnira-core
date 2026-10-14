# DEVNIRA company public wallet — genuinely held offline by the company

**The assistant, GitHub CI, and this repository must NEVER mint a production
company wallet on behalf of the company.** Only the company can securely
generate and retain the private ML-DSA/Dilithium87 key and corresponding
SS58-190 public account on its trusted computer; an invented checksum-valid
public address is not ownership. No mainnet exists yet.

## Existing tested native wallet tools

The pinned-Quantus fork patched with
`scripts/patch_dvn_wallet_cli.py` and
`scripts/patch_dvn_custody_signing.py` implements native Rust commands:

- `devnira-node key devnira --scheme standard --wallet-index 0`
  — **interactive terminal only** for a new secret. Back up the secret
  offline, never via email/chat/GitHub, and record only **Address** and
  **Pub key**. With `--words`, restore an EXISTING local secret via
  no-echo stdin. This is the underlying native CLI, not a Windows
  graphical signing wallet.
- `devnira-node key devnira-sign --message "..." --wallet-index 0`
  — read existing secret from protected stdin and cryptographically sign
  exactly a DEVNIRA company ownership challenge (NOT a transfer).
- `devnira-node key devnira-verify --message "..." --signature "0x..."
  --public-key "0x..." --expected-address "<your SS58-190 address>"`
  — verifiable full Dilithium87 ownership check.

These commands exist in the **patched locally compiled binary**, not in
the unmodified upstream Quantus node. Review the binary and SHA256 before
using it for real company custody. The CI mnemonic
`bottom drive obey lake curtain smoke basket hold race lonely fit walk`
is **public and permanently unfit** for real funds. Never use it.

## Strict signed company-to-genesis handoff

1. The company's owner uses the audited patched native CLI on a trusted,
   offline-capable device to create a **new**, locally backed-up private
   key; copy ONLY its public SS58-190 address and full public key.
2. Issue a 24-hour public ownership challenge:
   `python3 scripts/prepare_company_genesis_custody.py challenge
   --company-public-address "<PUBLIC DVN ADDRESS>"
   --output company-public-challenge.json`
3. Locally sign the challenge's exact `message` with
   `key devnira-sign`. Assemble a JSON certificate containing the
   challenge and `public_key_hex` / `signature_hex`. Secrets must
   NEVER be entered into that JSON.
4. Check the SHA256 of the trusted patched native verifier independently.
   Choose an **approved future UTC** launch time, *after* consensus audit.
5. Stage the off-chain reviewed proposal using:

```sh
python3 scripts/stage_company_genesis_local.py \
  --certificate /secure/local/company-public-certificate.json \
  --trusted-node /trusted/bin/devnira-node \
  --trusted-node-sha256 YOUR_INDEPENDENTLY_VERIFIED_64_HEX_SHA256 \
  --genesis-utc 2027-04-01T00:00:00+00:00 \
  --output-dir /secure/new-dvn-public-genesis-review
```

The launch date above is an EXAMPLE, not an approved timestamp. Output
directory must be new and outside the public repository. Files contain only
PUBLIC but pre-release sensitive account/launch data. Review grants carefully.

## What this does NOT do

Output `proposed-genesis-reviewed-NOT-LIVE.json` includes the verified
company **public** account and staged immutable 3M liquid + 7M locked /
12 Gregorian cliffs. It does not create an independent Substrate ChainSpec,
activate V2, prove governance immutability, sign an extrinsic, install a
wallet, issue coins, or deploy a blockchain. Those remain separate Stage 2
implementation and third-party review gates.
