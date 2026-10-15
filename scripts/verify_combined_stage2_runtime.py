#!/usr/bin/env python3
"""Verify DVN economic and V2 preflight changes coexist in ONE compiled source tree.

Only a fail-closed DEVELOPMENT check. Active V1 4.3.0 prover remains, with
user extrinsics disabled; this never attests production ZK V2 or Genesis.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

FILES={
    "runtime":"runtime/src/lib.rs",
    "configs":"runtime/src/configs/mod.rs",
    "mining":"pallets/mining-rewards/src/lib.rs",
    "vesting":"pallets/vesting/src/lib.rs",
    "genesis":"runtime/src/genesis_config_presets/mod.rs",
    "wormhole":"pallets/wormhole/src/lib.rs",
    "tree":"pallets/zk-tree/src/tree.rs",
    "chain_spec":"node/src/chain_spec.rs",
    "network_guard":"node/src/command.rs",
    "workspace":"Cargo.toml",
}
CONDITIONS={
    "eight_decimal_unit":("runtime","pub const UNIT: Balance = 100_000_000;"),
    "hard_max_supply":("runtime","pub const MAX_SUPPLY: Balance = 100_000_000 * UNIT;"),
    "independent_dev_runtime_name":("runtime","devnira-8dec-inert-dev-runtime"),
    "address_prefix_190":("configs","pub const SS58Prefix: u8 = 190;"),
    "actual_miner_only_90m_cap":("configs","type MiningCap = ConstU128<{ 90_000_000 * UNIT }>;"),
    "actual_mined_storage":("mining","pub type MinedSubsidy<T: Config>"),
    "actual_pending_storage":("mining","pub type PendingSubsidy<T: Config>"),
    "zero_legacy_issuer_path":("mining","pub mod devnira_emission;"),
    "immutable_founder_grants":("vesting","ImmutableGenesisScheduleCount"),
    "exact_vesting_pot":("vesting","type ExactGenesisFunding: Get<bool>;"),
    "economically_inert_genesis_mode":("configs","type ExactGenesisFunding = frame_support::traits::ConstBool<false>;"),
    "genesis_pot_ed_switch":("genesis","let pot_funding = if"),
    "v2_22pi_preflight_in_same_wormhole":("wormhole","DEVNIRA_V2_22_PI_PREFLIGHT_NO_SETTLEMENT"),
    "used_nullifiers_state":("wormhole","UsedNullifiers::<T>::contains_key(nullifier)"),
    "real_historical_block_lookup":("wormhole","frame_system::Pallet::<T>::block_hash"),
    "blocked_transfers":("configs","type BaseCallFilter = DvnResearchOnlyCallFilter;"),
    "no_wallet_dispatch":("configs","matches!(call, RuntimeCall::Timestamp(_) | RuntimeCall::System(_))"),
    "foreign_chain_blocked":("network_guard","DEVNIRA PRE-RELEASE: only --chain dev or --chain devnira-local"),
    "eight_decimal_metadata":("chain_spec","json!(8)"),
    "native_DVN_symbol":("chain_spec",'json!("DVN")'),
    "distinct_chain_id":("chain_spec",'with_id("devnira-8dec-inert-dev")'),
    "no_legacy_v1_spend_activation":("workspace", '=4.3.0"'),
    "legacy_v1_zk_tree_still_inert":("tree","pub const AMOUNT_SCALE_DOWN_FACTOR: u128 = 10_000_000_000;"),
    "legacy_v1_wormhole_still_inert":("wormhole","pub const SCALE_DOWN_FACTOR: u128 = 10_000_000_000;"),
}
def verify(root:Path)->dict:
    texts={}
    for name,path in FILES.items():
        try:
            texts[name]=(root/path).read_text(encoding="utf-8")
        except (OSError,UnicodeError) as exc:
            raise ValueError("Missing required pinned Rust source: "+path) from exc
    passed={name:needle in texts[file] for name,(file,needle) in CONDITIONS.items()}
    # Fail closed if a proof helper was accidentally promoted to callable
    # unverified transaction without an independently reviewed new gate.
    dangerous=(
        "impl frame_support::traits::Contains<RuntimeCall> for DvnResearchOnlyCallFilter"
        not in texts["configs"]
        or "pub(crate) fn devnira_v2_leaf_chain_preflight" not in texts["wormhole"]
        or "pub fn devnira_v2_leaf_chain_preflight" in texts["wormhole"]
        or 'with_id("devnira-mainnet-v1")' in texts["chain_spec"]
    )
    failed=[name for name,ok in passed.items() if not ok]
    if dangerous:
        failed.append("V2 admission helper was exposed or inert runtime call filter removed")
    if failed:
        raise ValueError("NOT A VALID INERT COMBINED RUNTIME: "+", ".join(failed))
    return {
      "schema":"devnira-8decimal-economics-v2-preflight-single-source-v1",
      "all_source_safety_checks_passed":True,
      "number_of_checks":len(CONDITIONS)+1,
      "user_transactions_enabled":False,
      "active_v2_proof_verifier":False,
      "real_genesis_built":False,
      "actual_gpu_network_proven":False,
      "independent_mainnet_ready":False,
      "warning":"COMPILED DEVELOPMENT RESEARCH ONLY. Legacy 4.3.0 proofs remain and cannot authorize transfers."
    }

def main()->None:
    a=argparse.ArgumentParser()
    a.add_argument("pinned_patched_chain_source",type=Path)
    a.add_argument("--json",type=Path)
    args=a.parse_args()
    report=verify(args.pinned_patched_chain_source)
    if args.json:
        args.json.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,sort_keys=True))

if __name__=="__main__":
    main()
