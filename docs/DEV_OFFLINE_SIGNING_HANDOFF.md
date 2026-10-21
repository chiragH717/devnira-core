# DEVNIRA DEV-only offline signer binding to actual finalized extrinsic (NO WALLET)

This new integration connects two-node read-only signing intent to live finalized
transaction acceptance. It does NOT derive keys, generate mnemonic, sign or
authorize production transfers.

## Prepare (two real DEV nodes, public data ONLY)

Environment inputs: DVN_TRUSTED_DEV_GENESIS, DVN_TEST_FROM_SS58,
DVN_TEST_TO_SS58, DVN_TEST_AMOUNT_UNITS, DVN_DEV_MAX_FEE_UNITS, DVN_INTENT_FILE.

    python3 -m scripts.dvn_last_acceptance --prepare-intent

The SHA256-bound intent records exact DEV genesis, canonical finalized block
height/hash, u32 nonce, integer balance/fee, SS58 190, 8 decimals, runtime spec,
transaction version and Blake2b256 metadata. Both independent local nodes
must agree; finalized hash and metadata are re-checked before returning.

## External isolated DEV signer requirements (NOT implemented yet)

An approved offline ML-DSA-87 signer must construct exact runtime SCALE call,
metadata/extension payload and mortal era, and sign with pinned upstream
FIPS-204 context QUANTUS_EXTRINSIC. Standard sr25519 or ed25519 is NOT
compatible with the Quantus-derived DEVNIRA runtime. The signer must not
use company treasury funds, production private keys, seeds or phrases.

After generating public fully signed SCALE bytes, prepare an INFORMATIONAL
(not cryptographically signed) JSON claim with EXACT keys:

    {
      "schema":"devnira-offline-dev-signed-extrinsic-binding-v1",
      "intent_sha256":"<64 lowercase SHA256 hex>",
      "signed_extrinsic_blake2b256":"0x<64 lowercase Blake2b hex>",
      "sender_ss58_190":"<valid DEV-only public address>",
      "signing_context":"QUANTUS_EXTRINSIC",
      "runtime":"devnira-8dec-native-dev-test-runtime"
    }

This claim is NOT a valid signature by itself. The new program binds it to
the unchanged unsigned intent and actual signed bytes; real signature
verification occurs only when the native chain accepts the transaction.
It then verifies that the same exact signed byte hash appears in a
finalized block on both DEV nodes, with precise balance credit, nonce,
fee and issuance accounting, and that identical replay is rejected.

## One final manual run after external prerequisites exist

Set DVN_INTENT_FILE, DVN_SIGNER_CLAIM_FILE, DVN_SIGNED_DEV_EXTRINSIC,
DVN_TRUSTED_DEV_GENESIS, DVN_V2_FINALIZED_HEIGHT, DVN_PRODUCTION_REVISION.

    python3 -m scripts.dvn_last_acceptance --run

This is NOT automatically run by PR CI and will FAIL in the current
DEV runtime because independent V2 header mode is disabled. Approved
production VK and native+WASM custody settlement, external GPU mining,
signed Windows/Android wallets, company Genesis and audit remain separate.
Do not publish private keys, deploy mainnet, or mistake a linkage JSON for
cryptographic ML-DSA verification.
