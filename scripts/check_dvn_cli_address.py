#!/usr/bin/env python3
"""Verify local native Dilithium keygen CLI outputs a single DEVNIRA public SS58.

Only parses public values. Never write company secrets, mnemonics, signatures,
or production key data to GitHub Actions.
"""
import argparse
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spec.ss58_company_account import decode_ss58_account, InvalidCompanyAddress

PUBLIC_ADDRESS_LINE = re.compile(r"^Address:\s*(\S+)\s*$")

def parse_public_wallet_output(text: str) -> str:
    if not isinstance(text, str):
        raise ValueError("wallet CLI output must be text")
    # New-key output may display mnemonic ONLY on trusted local TTY; never
    # treat such output as safe CI evidence.
    if any(item in text.lower() for item in ("secret phrase:", "seed hex:", "secret key:")):
        raise ValueError("CLI output includes secret material; do not upload")
    matches = [m.group(1) for line in text.splitlines() if (m := PUBLIC_ADDRESS_LINE.match(line.strip()))]
    if len(matches) != 1:
        raise ValueError("Expected exactly one DEVNIRA public receiving address")
    address = matches[0]
    try:
        decode_ss58_account(address, prefix=190)
    except InvalidCompanyAddress as exc:
        raise ValueError("CLI returned an invalid or wrong-network DVN account") from exc
    if "m/44'/900190'/0'/0'/0'" not in text:
        raise ValueError("CLI is still using Quantus or an unexpected derivation path")
    return address

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("public_cli_output", type=Path)
    args = parser.parse_args()
    address = parse_public_wallet_output(args.public_cli_output.read_text(encoding="utf-8"))
    print("PASS: DEVNIRA Dilithium test public account, SS58 190 and isolated hardened derivation.")
    print("Public address:", address, "(PUBLISHED TEST MNEMONIC ONLY; NOT A COMPANY WALLET)")
