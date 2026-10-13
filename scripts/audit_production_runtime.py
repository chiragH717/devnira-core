#!/usr/bin/env python3
"""Fail-closed DVN production readiness source audit.

A successful result is a necessary prerequisite, NOT a security audit or
proof that consensus is correct. Run before spending CI minutes on a release.
"""
import argparse
import re
from pathlib import Path

from audit_amount_encoding import check as check_amount_encoding

def audit(root: Path) -> None:
    check_amount_encoding(root)
    runtime = (root / "runtime/src/lib.rs").read_text()
    reward = (root / "pallets/mining-rewards/src/lib.rs").read_text()
    genesis = (root / "runtime/src/genesis_config_presets/mod.rs").read_text()
    chain_spec = (root / "node/src/chain_spec.rs").read_text()
    if 'Cow::Borrowed("devnira-runtime")' not in runtime:
        raise ValueError("STOP: runtime does not have an independent DEVNIRA identity")
    if not re.search(r"MAX_SUPPLY:\s*Balance\s*=\s*100_000_000\s*\*\s*UNIT", runtime):
        raise ValueError("STOP: 100 million DVN cap not compiled into runtime")
    if "remaining_supply.checked_div(&emission_divisor)" in reward:
        raise ValueError("STOP: upstream dynamic emission still active")
    if "Mined" not in reward and "mined" not in reward:
        raise ValueError("STOP: no miner-only issuance accounting evidenced in pallet")
    if "anchor_to_first_timestamp" not in genesis:
        raise ValueError("STOP: no on-chain genesis vesting schedule anchoring")
    if "devnira-mainnet" not in chain_spec:
        raise ValueError("STOP: independent DEVNIRA mainnet chain spec missing")
    print("Source-level release preflight passed. Runtime tests and security review remain mandatory.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("upstream_root", type=Path)
    audit(ap.parse_args().upstream_root)
