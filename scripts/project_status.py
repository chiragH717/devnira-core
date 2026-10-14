#!/usr/bin/env python3
"""Auditable DEVNIRA project state from checked-in sources (not a success claim).

No source file, green reference test or UI label can itself prove that a
production blockchain is deployed. Missing release evidence is shown explicitly.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def status(root: Path=ROOT) -> dict:
    proposal=json.loads((root/"config/genesis-proposal.json").read_text())
    c=proposal["company_treasury"]
    problems=[]
    if proposal["base_units_per_coin"]!=100_000_000:
        problems.append("Token base-unit configuration differs from 8 decimals")
    if proposal["max_supply_units"]!=10_000_000_000_000_000:
        problems.append("Total issuance does not equal 100M DVN")
    if proposal["mining_allocation_units"]!=9_000_000_000_000_000:
        problems.append("Mining budget does not equal 90M DVN")
    if c["instant_units"]!=300_000_000_000_000 or c["locked_units"]!=700_000_000_000_000:
        problems.append("Founder liquid/vesting split differs from approved 3M/7M")
    if c.get("public_address") is None:
        problems.append("Verified company DEVNIRA public address not available")
    problems.extend([
        "Active V2 Poseidon2 leaf, aggregator, prover and verifier not integrated end-to-end; pinned chain uses proof crates 4.3.0 while opt-in V2 decoder source is 4.4.0",
        "Independent 8-decimal DEVNIRA mainnet genesis has not been generated and tested",
        "Vesting pot existential-deposit fix is opt-in FRAME code only; actual independent DVN genesis remains unbuilt/unverified",
        "Windows secure transaction-signing wallet has not passed end-to-end tests",
        "Two live DVN nodes with NVIDIA and AMD GPU QPoW miners not validated",
        "Source revisions pinned for development; independent full-runtime build and security review incomplete",
    ])
    jobs=[
        "Opt-in REAL V2 Poseidon2 leaf recursively verified against fixed inner verifier key; rejects foreign same-layout proof key, tampered payout/fee (NOT linked into active runtime)",
        "Native Dilithium87 signing of public company-ownership challenges (NOT extrinsic transfers)",
        "Reward and immutable 12-month vesting on pinned upstream development runtime",
        "Windows SS58-190 receive and genesis-pinned finalized balance preview EXE (READ ONLY)",
        "NVIDIA CUDA and AMD Vulkan/WGPU miner source compiled without GPU hardware",
    ]
    return {
        "project":"DEVNIRA", "symbol":"DVN",
        "network":"NOT MAINNET READY",
        "company_treasury_policy":"one company-owned account; actual public address pending",
        "approved_supply": {
            "max_DVN":100_000_000,
            "mined_DVN":90_000_000,
            "liquid_company_DVN":3_000_000,
            "twelve_month_company_locked_DVN":7_000_000,
        },
        "last_user_verified_candidate_build":"four-component integration build #3; development only",
        "candidate_jobs_passed":jobs,
        "company_genesis_pot_identity":"canonical FRAME PalletId(qvesting), SS58 190; no real company account/funding yet",
        "network_selection":{"development_source_rejects_foreign_quantus_chain_ids":True,"actual_native_network_isolation_build_verified":False,"independent_mainnet_genesis":False},
        "proof_migration":{"opt_in_native_u64_leaf_private_public_parser_tests":True,"opt_in_no_std_compile":True,"opt_in_native_private_public_batch_amount_proofs":True,"opt_in_overflow_safe_bps_fee_proof":True,"opt_in_tampered_public_input_rejection":True,"opt_in_real_recursive_fixed_verifier_key_test":True,"opt_in_same_layout_foreign_key_rejected":True,"opt_in_public_dev_verifier_artifacts_with_sha256":True,"active_v2_recursive_verifier":False,"active_v2_onchain_settlement":False,"chain_proof_dependency":"4.3.0","external_proof_candidate":"4.4.0","compatible_for_runtime_8dec_activation":False},
        "windows_wallet_capabilities":{"public_receive":True,"finalized_balance_reader":True,"signed_send":False,"real_genesis_pin_available":False},
        "gpu_test_evidence":{"nvidia_cuda_source_checked":True,"amd_wgpu_source_checked":True,"actual_nvidia_pow":False,"actual_amd_pow":False,"two_live_nodes":False},
        "known_blockers":problems,
        "economics_configuration_valid":not any("configuration" in p or "issuance" in p and "does not" in p or "budget" in p or "split" in p for p in problems),
    }

if __name__=="__main__":
    print(json.dumps(status(), indent=2))
