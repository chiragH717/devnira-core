#!/usr/bin/env python3
"""Patch actual upstream Rust node to produce DEVNIRA-native Dilithium wallets.

Native offline key generation is the first prerequisite for company custody.
This does NOT constitute a working signed-transaction sender or on-chain wallet.

Security invariants:
* Derive independent DEVNIRA hardened HD paths, never the Quantus coin types.
* Emit/check 190-SS58 addresses, not the Quantus 189 network.
* Mnemonic generation MUST require an interactive TTY (no CI secret leakage).
* Mnemonic/seed imports use upstream no-echo stdin instead of command line.
* Wallet signing must be tested separately with a real independent DVN runtime.
"""
import argparse
from pathlib import Path

# This is a new, project-specific private coin-type namespace. The apostrophe
# is part of the hardened Rust HD derivation path as upstream expects.
DVN_STANDARD_HD_COIN_TYPE = "900190'"
DVN_WORMHOLE_HD_COIN_TYPE = "900191'"

def replace_exact(source: str, old: str, new: str, expected: int=1) -> str:
    found = source.count(old)
    if found != expected:
        raise ValueError(f"DVN wallet patch source drift: expected {expected}, found {found}: {old[:75]}")
    return source.replace(old, new)

def patch(root: Path) -> None:
    command_file = root / "node/src/command.rs"
    cli_file = root / "node/src/cli.rs"
    crypto_file = root / "primitives/dilithium-crypto/src/scheme_macro.rs"
    genesis_file = root / "runtime/src/genesis_config_presets/mod.rs"
    cmd = command_file.read_text()
    cli = cli_file.read_text()
    crypto = crypto_file.read_text()
    genesis = genesis_file.read_text()

    cmd = replace_exact(cmd,
        "SensitiveBytes64, QUANTUS_DILITHIUM_CHAIN_ID,\n\tQUANTUS_WORMHOLE_CHAIN_ID,",
        "SensitiveBytes64,")
    cmd = replace_exact(cmd,
        "use zeroize::{Zeroize, Zeroizing};",
        "use zeroize::{Zeroize, Zeroizing};\n"
        "use std::io::IsTerminal;\n\n"
        "/// DEVNIRA-only, hardened HD coin-type namespaces; not the Quantus coin types.\n"
        "const DEVNIRA_STANDARD_HD_COIN_TYPE: &str = \"900190'\";\n"
        "const DEVNIRA_WORMHOLE_HD_COIN_TYPE: &str = \"900191'\";")
    cmd = replace_exact(cmd, "QUANTUS_DILITHIUM_CHAIN_ID", "DEVNIRA_STANDARD_HD_COIN_TYPE", 3)
    cmd = replace_exact(cmd, "QUANTUS_WORMHOLE_CHAIN_ID", "DEVNIRA_WORMHOLE_HD_COIN_TYPE", 3)
    cmd = replace_exact(cmd, "Ss58AddressFormat::custom(189)", "Ss58AddressFormat::custom(190)", 5)

    # Use a visibly DEVNIRA command rather than silently replacing Quantus
    # key semantics in a command still named quantus.
    cmd = replace_exact(cmd, "QuantusKeySubcommand::Quantus {", "QuantusKeySubcommand::Devnira {")
    cli = replace_exact(cli, "\tQuantus {", "\tDevnira {")

    # A newly generated secret must never be printed by an unattended job.
    # Imported secrets are stdin-only and their recovery phrases are not echoed.
    run_anchor = "\t\t\t\t} => {\n\t\t\t\t\t// Secrets are read from stdin, never from argv (see cli.rs)."
    run_safety = ("\t\t\t\t} => {\n"
        "\t\t\t\t\t// Do not create/output new company keys to unattended CI logs or pipes.\n"
        "\t\t\t\t\tif !*seed && !*words &&\n"
        "\t\t\t\t\t\t(!std::io::stdin().is_terminal() || !std::io::stdout().is_terminal()) {\n"
        "\t\t\t\t\t\treturn Err(sc_cli::Error::Input(\n"
        "\t\t\t\t\t\t\t\"DEVNIRA new-key generation requires a local interactive terminal\".into(),\n"
        "\t\t\t\t\t\t));\n"
        "\t\t\t\t\t}\n"
        "\t\t\t\t\t// Secrets are read from stdin, never from argv (see cli.rs).")
    cmd = replace_exact(cmd, run_anchor, run_safety)

    cmd = replace_exact(cmd, "Generating Quantus Standard address...", "Generating DEVNIRA Standard address...")
    cmd = replace_exact(cmd, "Generating wormhole address...", "Generating DEVNIRA wormhole address...")
    cmd = replace_exact(cmd, "XXXXXXXXXXXXXXX Quantus Account Details", "XXXXXXXXXXXXXXX DEVNIRA Account Details")
    cmd = replace_exact(cmd, "XXXXXXXXXXXXXXX Quantus Wormhole Details", "XXXXXXXXXXXXXXX DEVNIRA Wormhole Details")

    # sp_core::Pair::from_phrase is called by the native `key sign` CLI.
    # Without this path change it silently signs for a DIFFERENT account than
    # the `key devnira --words` HD wallet — a custody-breaking mismatch.
    crypto = replace_exact(crypto,
        "// Default derivation path for Quantus: m/44'/189189'/0'/0'/0'",
        "// DEVNIRA offline signing must use the same hardened keygen path.")
    crypto = replace_exact(crypto,
        "const DEFAULT_PATH: &str = \"m/44'/189189'/0'/0'/0'\";",
        "const DEFAULT_PATH: &str = \"m/44'/900190'/0'/0'/0'\";")

    # All public accounts in the genesis CLI/preset must use the same SS58
    # namespace as node RPC and offline native Dilithium87 wallet addresses.
    genesis = replace_exact(genesis,
        "sp_core::crypto::Ss58AddressFormat::custom(189)",
        "sp_core::crypto::Ss58AddressFormat::custom(190)")

    # Script is fail-closed: commit all file contents only after all checks.
    command_file.write_text(cmd)
    cli_file.write_text(cli)
    crypto_file.write_text(crypto)
    genesis_file.write_text(genesis)
    print("Patched native Rust node CLI and Dilithium sign path: key devnira, HD isolation, SS58 190, terminal-only new keys.")
    print("NOT COMPLETE: secure transaction signing, key-store encryption and independent DVN genesis not established.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream_root", type=Path)
    patch(parser.parse_args().upstream_root)
