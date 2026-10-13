#!/usr/bin/env python3
"""DEVNIRA release artifact audit.

This script deliberately requires concrete evidence from a single integrated
8-decimal DEVNIRA node and proof-system build. Upstream candidates, prototype
codecs, unsigned monitors and synthetic chain specs are NOT release evidence.
"""
import argparse
import json
from pathlib import Path

REQUIRED = {
    "zk_active_proof": ("active_poseidon2_v2", "prover_verifier_aggregator_v2", "valid_and_invalid_withdrawal_tests"),
    "runtime_genesis": ("native_wasm_dvn_runtime", "independent_genesis", "genesis_supply_100m_cap",
                        "liquid_3m_locked_7m", "calendar_vesting_enforced"),
    "windows_wallet": ("secure_key_storage", "address_generation", "signed_transfer_roundtrip",
                       "locked_balance_display", "windows_executable_test"),
    "gpu_testnet": ("two_node_sync", "qpow_mining_rewards", "nvidia_gpu_proof",
                    "amd_gpu_proof", "reorg_and_cap_tests"),
}

def audit(evidence: dict) -> list[str]:
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be a JSON object")
    missing = []
    # One network identity across all evidence; avoid mixing a Quantus development
    # chain build with DEVNIRA-specific wallet/miner tests.
    net = evidence.get("network")
    if net != "devnira-independent":
        missing.append("network: independent DVN identity not verified")
    genesis = evidence.get("genesis_hash")
    if not isinstance(genesis, str) or not genesis.startswith("0x") or len(genesis) != 66:
        missing.append("genesis_hash: missing valid 32-byte chain hash")
    for group, fields in REQUIRED.items():
        values = evidence.get(group, {})
        if not isinstance(values, dict):
            values = {}
        for field in fields:
            if values.get(field) is not True:
                missing.append(f"{group}.{field}: no passing integration evidence")
    return missing

def main():
    p = argparse.ArgumentParser()
    p.add_argument("evidence", type=Path)
    args = p.parse_args()
    missing = audit(json.loads(args.evidence.read_text()))
    if missing:
        print(f"NOT RELEASE READY: {len(missing)} required checks absent")
        for issue in missing:
            print("BLOCKED:", issue)
        raise SystemExit(1)
    print("Evidence checklist complete. Independent security audit and review still required.")

if __name__ == "__main__":
    main()
