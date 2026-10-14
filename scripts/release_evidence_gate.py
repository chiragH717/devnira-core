#!/usr/bin/env python3
"""DEVNIRA release artifact audit.

This script deliberately requires concrete evidence from a single integrated
8-decimal DEVNIRA node and proof-system build. Upstream candidates, prototype
codecs, unsigned monitors and synthetic chain specs are NOT release evidence.
"""
import argparse
import json
import re
from pathlib import Path

REQUIRED = {
    "zk_active_proof": ("active_poseidon2_v2", "prover_verifier_aggregator_v2", "valid_and_invalid_withdrawal_tests"),
    "runtime_genesis": ("native_wasm_dvn_runtime", "independent_genesis", "genesis_supply_100m_cap",
                        "liquid_3m_locked_7m", "calendar_vesting_enforced"),
    "windows_wallet": ("secure_key_storage", "address_generation", "signed_transfer_roundtrip",
                       "locked_balance_display", "windows_executable_test"),
    "gpu_testnet": ("two_node_sync", "qpow_mining_rewards", "nvidia_gpu_proof",
                    "amd_gpu_proof", "reorg_and_cap_tests"),
    "android_wallet": ("secure_hardware_backed_custody", "verified_genesis_pin",
                       "signed_transfer_roundtrip", "recovery_test", "production_app_build"),
    "pool": ("consensus_verified_shares", "duplicate_share_rejection",
             "consensus_reward_accounting", "actual_onchain_payouts", "audited_miner_endpoint"),
    "explorer": ("finalized_block_indexer", "reorg_recovery", "decoded_transaction_account_search",
                 "verified_supply_and_rewards", "public_explorer_security_review"),
    "website": ("verified_domain_dns_tls", "accurate_wallet_and_mining_disclosures",
                "signed_release_download_hashes", "legal_privacy_support",
                "production_deployment_smoke_test"),
    "operations": ("public_rpc_tls_and_rate_limits", "hardened_bootnodes_and_peers",
                   "monitoring_backup_recovery", "reproducible_signed_releases",
                   "independent_security_audit"),
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
    if (not isinstance(genesis, str)
            or re.fullmatch(r"0x[0-9a-fA-F]{64}", genesis) is None
            or genesis.lower() == "0x" + "0" * 64):
        missing.append("genesis_hash: missing independently verified nonzero 32-byte chain hash")
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
    print("Evidence checklist shape complete, NOT cryptographic attestation.")
    print("An independent human security review of signed artifacts and network remains required.")

if __name__ == "__main__":
    main()
