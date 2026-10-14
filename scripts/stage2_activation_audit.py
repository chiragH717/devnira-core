#!/usr/bin/env python3
"""Inspect ACTUAL pinned chain sources for missing Stage-2 activation wiring.

Source checks are NECESSARY, NEVER SUFFICIENT: a green source audit is not
cryptographic proof compatibility, consensus safety, independent genesis or
production approval. An opt-in V2 module must not be counted as active.
"""
import argparse
import json
import re
from pathlib import Path

ZK_PROOF_CRATES = (
    "qp-wormhole-circuit",
    "qp-wormhole-inputs",
    "qp-wormhole-prover",
    "qp-wormhole-verifier",
    "qp-wormhole-aggregator",
    "qp-zk-circuits-common",
)
MAX_ISSUANCE = 10_000_000_000_000_000

def check(root: Path, proposal: dict) -> dict:
    source_paths = {
        "runtime": "runtime/src/lib.rs",
        "workspace": "Cargo.toml",
        "tree": "pallets/zk-tree/src/tree.rs",
        "wormhole": "pallets/wormhole/src/lib.rs",
        "configs": "runtime/src/configs/mod.rs",
        "chain_spec": "node/src/chain_spec.rs",
        "genesis": "runtime/src/genesis_config_presets/mod.rs",
    }
    texts = {}
    for kind, path in source_paths.items():
        file = root / path
        try:
            texts[kind] = file.read_text(encoding="utf-8")
        except FileNotFoundError:
            texts[kind] = ""
    checks = {}
    runtime = texts["runtime"]
    checks["native_runtime_8_decimals"] = bool(re.search(
        r"pub const UNIT:\s*Balance\s*=\s*100_000_000\s*;", runtime))
    checks["runtime_100m_supply_cap"] = bool(re.search(
        r"pub const MAX_SUPPLY:\s*Balance\s*=\s*100_000_000\s*\*\s*UNIT\s*;", runtime))

    # Each proof crate must move coherently, NOT a single parser. A registry
    # version upgrade by itself does NOT certify those artifacts.
    manifest = texts["workspace"]
    for crate in ZK_PROOF_CRATES:
        match = re.search(
            rf"^{re.escape(crate)}\s*=\s*\{{[^\n]*?version\s*=\s*\"([^\"]+)\"",
            manifest, re.M)
        checks["proof_dependency_"+crate] = bool(match and match.group(1) == "=4.4.0")
    tree = texts["tree"]
    wormhole = texts["wormhole"]
    # An *added* hash_leaf_native_v2 function is INERT if active get_leaf_hash
    # still calls the old quantizing hash_leaf. Require the active callsite.
    callsite = re.search(r"fn get_leaf_hash\s*<[^>]+>\s*\([^)]*\)[^{]*\{(.{0,1500})\}",tree,re.S)
    checks["native_v2_leaf_selected_by_active_tree"] = bool(
        callsite and "hash_leaf_native_v2" in callsite.group(1)
        and "hash_leaf::<" not in callsite.group(1))
    checks["legacy_quantized_leaf_removed"] = bool(tree) and not (
        "u32::try_from(amount_u128 / AMOUNT_SCALE_DOWN_FACTOR)" in tree
        or "pub const AMOUNT_SCALE_DOWN_FACTOR: u128 = 10_000_000_000" in tree)
    checks["legacy_wormhole_amount_scale_removed"] = bool(wormhole) and not (
        "pub const SCALE_DOWN_FACTOR: u128 = 10_000_000_000" in wormhole)
    checks["active_wormhole_v2_batch_parser"] = bool(
        "DvnV2PrivateBatchPublicInputs" in wormhole
        and "DvnV2PublicBatchPublicInputs" in wormhole
        and "DvnV2LeafPublicInputs" in wormhole)
    # Empty/pinned V1 artifact names must not be mistaken for real V2 VK.
    checks["active_wormhole_v2_verifier_artifacts"] = bool(
        "DEVNIRA_V2_ACTIVE_PRIVATE_BATCH_VERIFIER_SHA256" in wormhole
        and "DEVNIRA_V2_ACTIVE_PUBLIC_BATCH_VERIFIER_SHA256" in wormhole
        and "DEVNIRA_V2_ACTIVE_LEAF_VERIFIER_SHA256" in wormhole)
    checks["runtime_v2_vesting_pot_enabled"] = bool(re.search(
        r"type ExactGenesisFunding\s*=\s*frame_support::traits::ConstBool<true>\s*;",
        texts["configs"]))
    checks["miner_only_budget_90m_in_runtime"] = bool(re.search(
        r"type MiningCap\s*=\s*ConstU128<\{\s*90_000_000\s*\*\s*UNIT\s*\}>;",
        texts["configs"]))
    spec = texts["chain_spec"]
    checks["independent_8decimal_live_chain_spec"] = (
        'with_id("devnira-mainnet-v1")' in spec
        and 'json!(8)' in spec and 'json!("DVN")' in spec
        and 'json!(190)' in spec)
    checks["genesis_has_real_company_address"] = isinstance(
        proposal.get("company_treasury"), dict) and bool(
        proposal["company_treasury"].get("public_address"))
    checks["genesis_has_approved_timestamp"] = type(
        proposal.get("genesis_timestamp_ms")) is int and proposal["genesis_timestamp_ms"] > 0
    checks["genesis_has_actual_runtime_allocation"] = (
        checks["genesis_has_real_company_address"]
        and checks["genesis_has_approved_timestamp"]
        and "devnira-mainnet" in texts["genesis"]
        and "ExactGenesisFunding" in texts["genesis"])
    result = {
        "schema": "devnira-stage2-source-integration-audit-v1",
        "development_only": True,
        "active_v2_integration_proven": False,
        "independent_8decimal_genesis_proven": False,
        "checks": checks,
        "missing": [key for key, passed in checks.items() if not passed],
        "external_proof_and_live_chain_testing_still_required": True,
    }
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("chain_source",type=Path)
    p.add_argument("--proposal",type=Path,default=Path("config/genesis-proposal.json"))
    p.add_argument("--report",type=Path)
    p.add_argument("--expect-blocked",action="store_true",
                   help="Dev CI: require candidate NOT to be mistaken for active chain")
    a = p.parse_args()
    report = check(a.chain_source,json.loads(a.proposal.read_text(encoding="utf-8")))
    data = json.dumps(report,sort_keys=True,indent=2)+"\n"
    if a.report:
        a.report.write_text(data,encoding="utf-8")
    print(data)
    if a.expect_blocked:
        if not report["missing"]:
            p.error("Unexpected source-gate transition: require independent manual audit")
        print(f"EXPECTED BLOCKED: {len(report['missing'])} missing source integrations")
    elif report["missing"]:
        p.error(f"Stage 2 NOT complete: {len(report['missing'])} missing source integrations")
    else:
        print("Source checks only, NOT activation: real recursive/root/nullifier proofs and an independent genesis are still required.")

if __name__=="__main__":
    main()
