#!/usr/bin/env python3
"""Add real Dilithium87 custody-challenge sign/verify CLI to pinned DEVNIRA node.

Upstream sc-cli does not expose `key sign` or `key verify` here. Do not call
missing subcommands, change proof outcomes, or use a mock signature. Instead:
- `key devnira-sign --message <public challenge>`: mnemonic via protected stdin;
  derive EXACT m/44'/900190'/index'/0'/0' key and output signature only.
- `key devnira-verify`: cryptographically verify ML-DSA-87 signed challenge,
  expected full public key AND SS58-190 company beneficiary account.
Neither command sends transactions, funds a genesis, or encrypts a wallet.
"""
import argparse
from pathlib import Path

CLI_VARIANTS = r'''
    /// Sign a DEVNIRA-specific address-bound custody challenge; never a transfer.
    /// Supply the mnemonic through private, no-echo stdin. Never in argv.
    #[command(name = "devnira-sign")]
    DevniraSign {
        #[arg(long)]
        message: String,
        #[arg(long, default_value_t = 0)]
        wallet_index: u32,
    },

    /// Verify the full Dilithium87 signature, public key, and native SS58-190 address.
    #[command(name = "devnira-verify")]
    DevniraVerify {
        #[arg(long)]
        message: String,
        #[arg(long)]
        signature: String,
        #[arg(long)]
        public_key: String,
        #[arg(long)]
        expected_address: String,
    },
'''

HELPERS = r'''
// BEGIN DEVNIRA REAL NATIVE DILITHIUM87 CUSTODY SIGNING
/// Prevent generic message-signing from becoming a signing oracle for
/// transactions or other chain/domain protocols. Company challenges are
/// one-purpose attestations, with independent expiry/nonce enforcement in
/// spec/verify_company_custody.py.
const DEVNIRA_CUSTODY_CHALLENGE_DOMAIN: &str =
    "DEVNIRA-COMPANY-GENESIS-OWNERSHIP-V1|devnira-mainnet-v1|";

fn validate_dvn_custody_challenge(message: &str) -> Result<(), sc_cli::Error> {
    if !message.starts_with(DEVNIRA_CUSTODY_CHALLENGE_DOMAIN)
        || message.len() > 1024
        || message.bytes().any(|b| b == 0 || b == b'\n' || b == b'\r')
    {
        return Err(sc_cli::Error::Input(
            "only a bounded DEVNIRA company genesis ownership challenge may be signed".into(),
        ));
    }
    Ok(())
}

fn devnira_sign_custody_challenge(
    mnemonic: &str,
    message: &str,
    wallet_index: u32,
) -> Result<String, sc_cli::Error> {
    validate_dvn_custody_challenge(message)?;
    // Matches the exact address returned by key devnira --scheme standard
    // --words --wallet-index N, *not* the old Quantus HD namespace.
    let path = format!("m/44'/900190'/{}'/0'/0'", wallet_index);
    let keypair = derive_key_from_mnemonic(mnemonic, None, &path)
        .map_err(|_| sc_cli::Error::Input("invalid DEVNIRA mnemonic or HD path".into()))?;
    let pair = Dilithium87Pair::from_keypair(keypair);
    let signed = pair.sign(message.as_bytes());
    Ok(format!("0x{}", hex::encode(signed.as_ref())))
}

fn devnira_verify_custody_challenge(
    signature_hex: &str,
    public_key_hex: &str,
    message: &str,
    expected_address: &str,
) -> Result<(), sc_cli::Error> {
    validate_dvn_custody_challenge(message)?;
    let sig_bytes = hex::decode(signature_hex.strip_prefix("0x").unwrap_or(signature_hex))
        .map_err(|_| sc_cli::Error::Input("invalid Dilithium87 signature hex".into()))?;
    let signature = Dilithium87SignatureWithPublic::from_bytes(&sig_bytes)
        .map_err(|_| sc_cli::Error::Input("invalid Dilithium87 signature length".into()))?;
    let public_bytes = hex::decode(public_key_hex.strip_prefix("0x").unwrap_or(public_key_hex))
        .map_err(|_| sc_cli::Error::Input("invalid Dilithium87 public key hex".into()))?;
    let public_key = <Dilithium87Public as sp_core::crypto::ByteArray>::from_slice(&public_bytes)
        .map_err(|_| sc_cli::Error::Input("invalid Dilithium87 public key length".into()))?;
    // The signature includes the full public key. Reject any inconsistent
    // claimed signer even if a valid signature exists for another account.
    if signature.public() != public_key {
        return Err(sc_cli::Error::Input("custody signature public key mismatch".into()));
    }
    let actual_address =
        AccountId32::from(public_key.clone()).to_ss58check_with_version(
            Ss58AddressFormat::custom(190),
        );
    if actual_address != expected_address {
        return Err(sc_cli::Error::Input(
            "signature public key does not derive expected DEVNIRA address".into(),
        ));
    }
    if !Dilithium87Pair::verify(&signature, message.as_bytes(), &public_key) {
        return Err(sc_cli::Error::Input("invalid company custody challenge signature".into()));
    }
    Ok(())
}
// END DEVNIRA REAL NATIVE DILITHIUM87 CUSTODY SIGNING

'''

MATCH_ARMS = r'''
                QuantusKeySubcommand::DevniraSign { message, wallet_index } => {
                    let secret = read_secret_from_stdin("DEVNIRA mnemonic (never use public CI keys for custody): ")?;
                    let signature = devnira_sign_custody_challenge(
                        secret.as_str(), message, *wallet_index
                    )?;
                    // Only the public signature is emitted, no mnemonic/seed/secret key.
                    println!("Signature: {}", signature);
                    Ok(())
                },
                QuantusKeySubcommand::DevniraVerify {
                    message, signature, public_key, expected_address,
                } => {
                    devnira_verify_custody_challenge(
                        signature, public_key, message, expected_address,
                    )?;
                    println!("Signature verifies correctly.");
                    Ok(())
                },
'''

RUST_TESTS = r'''
#[cfg(test)]
mod devnira_native_custody_signing_tests {
    use super::*;

    const PUBLIC_TEST_MNEMONIC: &str =
        "bottom drive obey lake curtain smoke basket hold race lonely fit walk";

    #[test]
    fn devnira_native_signature_matches_ss58_190_hd_address() {
        let expected = generate_quantus_key(
            QuantusAddressType::Standard, None,
            Some(PUBLIC_TEST_MNEMONIC.to_string()), 0, false,
        ).expect("TEST mnemonic must restore");
        let message = format!(
            "{}{}|{}|{}",
            DEVNIRA_CUSTODY_CHALLENGE_DOMAIN, expected.address,
            "a".repeat(64), 1800000000000u64,
        );
        let signature = devnira_sign_custody_challenge(
            PUBLIC_TEST_MNEMONIC, &message, 0,
        ).expect("TEST key should sign valid challenge");
        devnira_verify_custody_challenge(
            &signature, &expected.public_key_hex, &message, &expected.address,
        ).expect("signature must verify against derived HD address");

        assert!(devnira_verify_custody_challenge(
            &signature, &expected.public_key_hex, &(message.clone()+"tampered"),
            &expected.address,
        ).is_err(), "tampered challenge must not verify");
        assert!(devnira_verify_custody_challenge(
            &signature, &expected.public_key_hex, &message, "wrong-ss58-address",
        ).is_err(), "wrong company account must not verify");
        assert!(devnira_verify_custody_challenge(
            &signature, "0x00", &message, &expected.address,
        ).is_err(), "different public key must not verify");
        assert!(devnira_sign_custody_challenge(
            PUBLIC_TEST_MNEMONIC, "TRANSFER-ALL-COINS", 0,
        ).is_err(), "generic wallet signing is forbidden");
    }
}
'''

def replace_once(source: str, anchor: str, replacement: str, label: str) -> str:
    if source.count(anchor) != 1:
        raise ValueError(f"DVN custody signing patch source drift: {label}")
    return source.replace(anchor, replacement, 1)

def patch(root: Path) -> None:
    cli_path = root / "node/src/cli.rs"
    cmd_path = root / "node/src/command.rs"
    cli = cli_path.read_text()
    cmd = cmd_path.read_text()
    if "DevniraSign {" in cli or "BEGIN DEVNIRA REAL NATIVE" in cmd:
        raise ValueError("DVN custody signing patch already installed")
    # Stage both in memory, write only after *all* source anchors match.
    cli = replace_once(cli, "\tDevnira {",
                       CLI_VARIANTS + "\tDevnira {", "devnira CLI enum")
    cmd = replace_once(cmd,
        "use qp_dilithium_crypto::{traits::WormholeAddress, Dilithium87Pair};",
        "use qp_dilithium_crypto::{traits::WormholeAddress, Dilithium87Pair, Dilithium87Public, Dilithium87SignatureWithPublic};",
        "native Dilithium87 type imports")
    cmd = replace_once(cmd, "/// Parse and run command line arguments\n",
                       HELPERS + "/// Parse and run command line arguments\n",
                       "native wallet signing helper insertion")
    cmd = replace_once(cmd,
        "QuantusKeySubcommand::Devnira {",
        MATCH_ARMS + "QuantusKeySubcommand::Devnira {",
        "DEVNIRA key subcommand dispatch")
    if "mod devnira_native_custody_signing_tests" in cmd:
        raise ValueError("DVN native wallet proof tests already installed")
    cmd += "\n" + RUST_TESTS
    cli_path.write_text(cli)
    cmd_path.write_text(cmd)
    print("Enabled actual native DEVNIRA key devnira-sign/verify custody commands; no secret argv.")
    print("NOT a signed transaction wallet. Independent genesis and active V2 proof path still BLOCKED.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream_root", type=Path)
    patch(parser.parse_args().upstream_root)
