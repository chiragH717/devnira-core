# Windows native public-wallet bootstrap

DEVNIRA's Windows GUI (`DEVNIRA-Company-Wallet-Setup-NO-SEND.exe`) can
prepare the actual COMPANY'S public SS58-190 account **without any mainnet**,
but it requires a **separately built patched native Dilithium87 executable**.

## Build and test native Rust wallet executable

A new **experimental**, explicitly separate
[Windows native company CLI workflow](../.github/workflows/windows-native-company-cli.yml)
checks out the **exact** pinned Quantus source, applies DEVNIRA isolated
HD derivation, strict native sign/verify challenge and foreign-network
lockout source patches, then attempts a full Windows `quantus-node.exe`
build. It uses a **public test-only mnemonic**, validates SS58-190 output,
rejects Quantus mainnet selector, and publishes the unsigned
`DEVNIRA-Offline-Key-CLI-NOT-MAINNET.exe` with SHA256 only IF the actual
Windows native Rust build/test succeeds.

**A workflow definition is NOT proof of a successful build.** Inspect
Actions before trusting an artifact. The executable contains a development
V1 chain runtime; NEVER use it to join public DVN mainnet, sign transfers,
mine real rewards, or trust a native state root.

## Local owner's workflow

1. Download and independently inspect the actual signed-off native-source
   build. Cross-check SHA256 outside the GUI; it must match the
   executable's contents and your trusted source revision.
2. Open the Windows GUI **Offline Company Wallet** tab. Point to that
   native EXE and enter its lowercase SHA256. Click the hash-check and
   copy-Command button. This code never accepts mnemonic or secret keys.
3. Open your own private **PowerShell** window, paste the hash-rechecking
   offline key-generation command; protect **all recovery words offline**.
   A published CI mnemonic is NOT private: never reuse it.
4. Save the public address and public Dilithium87 key only. Complete the
   24-hour address-bound signing challenge locally, and retain the resulting
   public certificate for actual genesis sign-off. Do not publish it in
   GitHub until security review/launch approval.
5. Genesis remains OFF-CHAIN until the active V2 verifier/aggregator,
   independent eight-decimal FRAME/WASM runtime and genuine chain spec pass
   the runtime and security gates.

No part of the GUI or GitHub workflow generates or retains company
production private keys. Wallet **SEND** is not available.
