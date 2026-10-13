#!/usr/bin/env python3
"""Generate a reviewable DVN allocation schedule from PUBLIC beneficiary addresses.

Input example (JSON): [{"public_address": "...", "instant_units": 300000000000000,
                         "vested_units": 700000000000000}]
Amounts are integer base units, not DVN decimal strings.
This does not construct the chain state or create/manage wallets.
"""
import argparse
import json
from datetime import datetime
from pathlib import Path
from spec.genesis_allocations import Beneficiary
from spec.genesis_manifest import build_manifest

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--beneficiaries", type=Path, required=True, help="Public addresses and integer base-unit allocations")
    parser.add_argument("--genesis-utc", required=True, help="ISO-8601 timestamp with timezone, e.g. 2027-01-31T12:00:00+00:00")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = json.loads(args.beneficiaries.read_text())
    if not isinstance(raw, list):
        raise ValueError("beneficiaries must be a JSON list")
    rows = [Beneficiary(**entry) for entry in raw]
    manifest = build_manifest(datetime.fromisoformat(args.genesis_utc), rows)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"Off-chain manifest generated: {args.output} — NOT a launch-ready genesis")

if __name__ == "__main__":
    main()
