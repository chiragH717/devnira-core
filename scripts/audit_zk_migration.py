#!/usr/bin/env python3
"""Fail-closed DVN ZK migration preflight over actual FRAME chain sources.

This is deliberately conservative: passing static checks is NOT proof-system
compatibility, but it blocks the known V1 12-decimal u32 leaf from being
mistaken for DVN's eight-decimal, canonical u64 encoding.
"""
import argparse
import re
from pathlib import Path

DVN_UNIT = 100_000_000
DVN_CAP_UNITS = 10_000_000_000_000_000
GOLDILOCKS_PRIME = 0xFFFF_FFFF_0000_0001

def audit(root: Path) -> dict:
    paths = {
        "runtime": root / "runtime/src/lib.rs",
        "zk": root / "pallets/zk-tree/src/tree.rs",
        "wormhole": root / "pallets/wormhole/src/lib.rs",
        "configs": root / "runtime/src/configs/mod.rs",
        "workspace": root / "Cargo.toml",
    }
    sources = {key: path.read_text() for key, path in paths.items()}
    errors = []

    runtime = sources["runtime"]
    zk = sources["zk"]
    wormhole = sources["wormhole"]
    configs = sources["configs"]
    workspace = sources["workspace"]

    if not re.search(r"pub const UNIT:\s*Balance\s*=\s*100_000_000\s*;", runtime):
        errors.append("runtime UNIT is not exactly 100,000,000 base units/DVN")
    if not re.search(r"pub const MAX_SUPPLY:\s*Balance\s*=\s*100_000_000\s*\*\s*UNIT\s*;", runtime):
        errors.append("runtime MAX_SUPPLY is not 100 million DVN")
    if "u32::try_from(amount_u128 / AMOUNT_SCALE_DOWN_FACTOR)" in zk:
        errors.append("ZK-tree still saturates/quantizes native amount into u32 V1 leaf")
    if "amount_quantized" in zk and "u32::MAX" in zk:
        errors.append("ZK-tree still references saturating u32 leaf amount")
    if "pub const AMOUNT_SCALE_DOWN_FACTOR: u128 = 10_000_000_000;" in zk:
        errors.append("ZK-tree still uses upstream 10^10 quantum")
    if "pub const SCALE_DOWN_FACTOR: u128 = 10_000_000_000;" in wormhole:
        errors.append("Wormhole still uses upstream 10^10 quantum")
    if "pub const VestingPayoutQuantum: Balance = pallet_wormhole::SCALE_DOWN_FACTOR;" not in configs:
        errors.append("Vesting payout quantum needs manual reassessment")
    for crate in ("qp-wormhole-circuit", "qp-wormhole-inputs", "qp-wormhole-prover", "qp-wormhole-verifier"):
        if not re.search(rf"^{re.escape(crate)}\s*=\s*\{{[^\n]*version\s*=\s*\"=4\.3\.0\"", workspace, flags=re.MULTILINE):
            errors.append(f"{crate} source/version changed: validate full circuit/proof migration")
        else:
            errors.append(f"{crate} remains upstream V1 4.3.0: recompile coordinated V2 circuit/prover/verifier")
    assert DVN_CAP_UNITS < GOLDILOCKS_PRIME, "DVN amount cannot be one Goldilocks felt"
    return {"passed": not errors, "errors": errors, "cross_layer_sources": [str(p.relative_to(root)) for p in paths.values()]}

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source_root", type=Path)
    args = ap.parse_args()
    report = audit(args.source_root)
    print("DEVNIRA eight-decimal ZK production preflight")
    for message in report["errors"]:
        print("BLOCKED:", message)
    if report["errors"]:
        raise SystemExit(f"Production migration NOT READY: {len(report['errors'])} unresolved checks")
    print("Static preflight passed; still require live proof and withdrawal verification.")

if __name__ == "__main__":
    main()
