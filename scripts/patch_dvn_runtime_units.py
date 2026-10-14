#!/usr/bin/env python3
"""Stage the *actual* 8-decimal DEVNIRA FRAME runtime constants offline.

IMPORTANT: cannot be activated until ZK leaf/circuit/prover/verifier are
migrated together. This is an atomic, fail-closed source patch, NOT genesis.
"""
from pathlib import Path
import argparse

REPLACEMENTS = (
    ('alloc::borrow::Cow::Borrowed("quantus-runtime")', 'alloc::borrow::Cow::Borrowed("devnira-runtime")', 2),
    ("pub const UNIT: Balance = 1_000_000_000_000;", "pub const UNIT: Balance = 100_000_000;", 1),
    ("pub const MILLI_UNIT: Balance = 1_000_000_000;", "pub const MILLI_UNIT: Balance = 100_000;", 1),
    ("pub const MICRO_UNIT: Balance = 1_000_000;", "pub const MICRO_UNIT: Balance = 100;", 1),
    ("pub const MAX_SUPPLY: Balance = 21_000_000 * UNIT;", "pub const MAX_SUPPLY: Balance = 100_000_000 * UNIT;", 1),
)

def patch(root: Path) -> None:
    runtime_file = root / "runtime/src/lib.rs"
    zk_tree_file = root / "pallets/zk-tree/src/tree.rs"
    wormhole_file = root / "pallets/wormhole/src/lib.rs"
    config_file = root / "runtime/src/configs/mod.rs"

    runtime = runtime_file.read_text()
    zk = zk_tree_file.read_text()
    wormhole = wormhole_file.read_text()
    config = config_file.read_text()

    # Refuse to activate a real 8-decimal runtime with an unsafe/mismatching
    # Quantus V1 proof system. No overrides or bypass flags by design.
    if "pub const AMOUNT_SCALE_DOWN_FACTOR: u128 = 10_000_000_000;" in zk:
        raise ValueError("STOP: ZK tree still uses V1 12-decimal scaling; migrate verified V2 circuit first")
    if "pub const SCALE_DOWN_FACTOR: u128 = 10_000_000_000;" in wormhole:
        raise ValueError("STOP: Wormhole V1 scaling incompatible with 8-decimal DVN")
    if "u32::try_from(amount_u128 / AMOUNT_SCALE_DOWN_FACTOR)" in zk:
        raise ValueError("STOP: ZK tree still truncates/saturates amount to u32")
    if "type MiningCap = ConstU128<{ 90_000_000 * UNIT }>;" not in config:
        raise ValueError("STOP: production miner-only 90M cap not integrated")
    if "ImmutableGenesisScheduleCount" not in (root / "pallets/vesting/src/lib.rs").read_text():
        raise ValueError("STOP: protected founder genesis vesting not integrated")
    # A quantum/u32 source edit alone cannot produce V2 cryptographic proofs.
    # The pinned Quantus chain depends on qp-wormhole 4.3.0 while the
    # pinned V2 candidate source is built from 4.4.0. Even after the old
    # quantum is removed, never silently activate an 8-decimal native
    # runtime while a legacy 4.3.0 prover/verifier can still be linked.
    import re
    manifest=(root / "Cargo.toml").read_text(encoding="utf-8")
    proof_crates=(
        "qp-wormhole-circuit", "qp-wormhole-inputs",
        "qp-wormhole-prover", "qp-wormhole-verifier",
        "qp-wormhole-aggregator", "qp-zk-circuits-common",
    )
    for crate in proof_crates:
        if not re.search(rf"^{re.escape(crate)}\\s*=\\s*\\{{[^\\n]*version\\s*=\\s*\"[^\"]+\"",manifest,re.M):
            raise ValueError(f"STOP: pinned proof version for {crate} is missing or changed")
        if re.search(rf"^{re.escape(crate)}\\s*=\\s*\\{{[^\\n]*version\\s*=\\s*\"=4\\.3\\.0\"",manifest,re.M):
            raise ValueError(
                f"STOP: {crate} still uses Quantus V1 4.3.0 proof layout; "
                "full leaf/aggregate/prover/verifier migration required"
            )

    next_runtime = runtime
    for old, new, occurrences in REPLACEMENTS:
        if next_runtime.count(old) != occurrences:
            raise ValueError(f"Source drift or previously patched: {old}")
        next_runtime = next_runtime.replace(old, new)
    runtime_file.write_text(next_runtime)
    print("Staged DVN runtime units and identity; all known local legacy blockers absent.")
    print("NOT A RELEASE: still require linked live V2 proof and independent genesis tests.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream_root", type=Path)
    patch(parser.parse_args().upstream_root)
