#!/usr/bin/env python3
"""Compose merged DEVNIRA branches in ONE pinned native/WASM PRE-WALLET devnet.

NO production mainnet, wallet, ZK withdrawals, or live signed transfer claim.
Only native signed Balances keep_alive is exposed on ephemeral DEV chain;
the separate native custody/headers are intentionally NOT user-callable.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from scripts.guard_dvn_network_identity import patch as guard
from scripts.patch_isolated_dvn_8decimal_runtime import patch as inert_8decimal
from scripts.patch_signed_8decimal_native_testnet import patch as signed_native
from scripts.patch_zk_tree_native_v2 import patch as native_leaf
from scripts.patch_zk_v2_native_custody_ledger import patch as custody
from scripts.patch_zk_v2_custody_commitment import patch as receipt
from scripts.patch_zk_v2_custody_merkle_depth16 import patch as merkle
from scripts.patch_zk_v2_header_root_bridge import patch as header

ORDER = (
    ("isolate_all_foreign_networks", guard),
    ("separate_inert_8decimal_identity", inert_8decimal),
    ("native_signed_balances_ONLY_no_V1_recorder", signed_native),
    ("canonical_native_leaf", native_leaf),
    ("backed_internal_custody", custody),
    ("poseidon_receipt_commitment", receipt),
    ("independent_depth16_merkle", merkle),
    ("default_disabled_V2_header_bridge", header),
)
WATCH = (
    "node/src/command.rs",
    "node/src/chain_spec.rs",
    "runtime/src/lib.rs",
    "runtime/src/configs/mod.rs",
    "pallets/frame-system/src/lib.rs",
    "pallets/zk-tree/src/lib.rs",
    "pallets/zk-tree/src/tree.rs",
    "pallets/wormhole/src/lib.rs",
)
# All checks are source assertions after actual patch composition;
# compilation and chain-spec validation are required IN ADDITION to these.
INVARIANTS = {
    "node/src/command.rs": (
        "DEVNIRA PRE-RELEASE: only --chain dev or --chain devnira-local",
    ),
    "node/src/chain_spec.rs": (
        "devnira-8dec-native-dev-test",
    ),
    "runtime/src/lib.rs": (
        "DEVNIRA_DEV_ONLY_SIGNED_NATIVE_BALANCES_WITHOUT_V1_WORMHOLE",
        "pub const UNIT: Balance = 100_000_000;",
        "CheckGenesis<Runtime>",
        "CheckNonce<Runtime>",
        "ChargeTransactionPayment<Runtime>",
    ),
    "runtime/src/configs/mod.rs": (
        "type BaseCallFilter = DvnResearchOnlyCallFilter;",
        "RuntimeCall::Balances(pallet_balances::Call::transfer_keep_alive",
    ),
    "pallets/frame-system/src/lib.rs": (
        "DEVNIRA_V2_HEADER_MODE_DISABLED_UNTIL_SEPARATE_RUNTIME_APPROVAL",
        "DvnV2HeaderRootCandidate<T:Config>",
    ),
    "pallets/wormhole/src/lib.rs": (
        "DEVNIRA_V2_NATIVE_ESCROW_BACKING_INTERNAL_NO_DISPATCH",
        "DEVNIRA_V2_CUSTODY_COMMITMENTS_STORAGE_NO_FINALIZED_ROOT",
        "DEVNIRA_V2_CUSTODY_MERKLE_DEPTH16_NON_HEADER",
        "Self::devnira_v2_append_merkle_internal(id,commitment)?;",
        "frame_system::DvnV2HeaderRootCandidate::<T>::put(root)",
    ),
    "pallets/zk-tree/src/lib.rs": (
        "frame_system::DvnV2HeaderMode::<T>::get()",
        "frame_system::DvnV2HeaderRootCandidate::<T>::take()",
    ),
}
def verify_post_composition(root: Path) -> dict[str, str]:
    d = {}
    for relative in WATCH:
        raw = (root / relative).read_bytes()
        contents = raw.decode("utf-8")
        for expected in INVARIANTS.get(relative, ()):
            if expected not in contents:
                raise ValueError("STOP: missing integration invariant "+relative+": "+expected)
        d[relative] = hashlib.sha256(raw).hexdigest()
    runtime = (root / "runtime/src/lib.rs").read_text("utf-8")
    config = (root / "runtime/src/configs/mod.rs").read_text("utf-8")
    tree = (root / "pallets/zk-tree/src/lib.rs").read_text("utf-8")
    if "WormholeProofRecorderExtension<Runtime>" in runtime:
        raise ValueError("STOP: legacy 12-decimal V1 proof recorder still enabled")
    # Gate ONLY native balances call; no utility/proxy/batch/old V1 wormhole.
    from scripts.patch_signed_8decimal_native_testnet import FILTER_AFTER
    if config.count(FILTER_AFTER) != 1 or "RuntimeCall::Wormhole" in FILTER_AFTER:
        raise ValueError("STOP: unexpected native DEV allowlist")
    if "DvnV2HeaderMode::<T>::put(true)" in tree:
        raise ValueError("STOP: V2 header mode activated by unreviewed runtime")
    if "pub fn devnira_v2_record_native_escrow_internal" in (root / "pallets/wormhole/src/lib.rs").read_text("utf-8"):
        raise ValueError("STOP: custody was accidentally made public")
    return d

def assemble(root: Path) -> dict:
    root = Path(root)
    if not (root/"runtime/src/lib.rs").is_file():
        raise ValueError("STOP: pinned FRAME source absent")
    completed=[]
    for name, fn in ORDER:
        fn(root)
        completed.append(name)
    digests=verify_post_composition(root)
    return {
        "schema":"devnira-prewallet-composed-native8-devnet-v1",
        "classification":"DEVELOPMENT ONLY: NO ACTIVE V2 SEND OR MAINNET",
        "stages":completed,
        "sha256_changed_source":digests,
        "native_dev_balance_transfer_allowlist":True,
        "v1_proof_recorder":False,
        "production_v2_header_mode_activated":False,
        "v2_proof_verifier_activated":False,
        "production_vk_approved":False,
        "signed_transfer_roundtrip_verified":False,
        "two_nodes_finalized_verified":False,
        "genesis_company_treasury_approved":False,
        "wallet_release_approved":False,
        "mainnet_approved":False,
    }

def main():
    p=argparse.ArgumentParser(description="Compose prewallet DEV ONLY source; do NOT launch")
    p.add_argument("pinned_upstream_checkout",type=Path)
    p.add_argument("--report",type=Path)
    args=p.parse_args()
    result=assemble(args.pinned_upstream_checkout)
    print(json.dumps(result,sort_keys=True))
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
if __name__=="__main__":main()
