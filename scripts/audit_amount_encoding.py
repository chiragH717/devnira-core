#!/usr/bin/env python3
"""Fail-closed preflight for importing the Quantus runtime into DEVNIRA.

This checks a consensus-critical amount encoding mismatch. It does not claim
that passing this check would make the chain production ready.
"""
import argparse
import re
from pathlib import Path

DVN_UNIT = 100_000_000

def check(root: Path) -> None:
    runtime = (root / "runtime/src/lib.rs").read_text()
    tree = (root / "pallets/zk-tree/src/tree.rs").read_text()
    unit_match = re.search(r"pub const UNIT:\s*Balance\s*=\s*([\d_]+)", runtime)
    quantum_match = re.search(r"pub const AMOUNT_SCALE_DOWN_FACTOR:\s*u128\s*=\s*([\d_]+)", tree)
    if not unit_match or not quantum_match:
        raise ValueError("Cannot verify runtime unit or ZK amount quantum; STOP")
    runtime_unit = int(unit_match.group(1).replace("_", ""))
    quantum = int(quantum_match.group(1).replace("_", ""))
    if runtime_unit != DVN_UNIT:
        raise ValueError(f"Runtime uses {runtime_unit} base units/coin, expected {DVN_UNIT}. STOP: needs unit, fee, proof and circuit migration")
    if quantum > DVN_UNIT or DVN_UNIT % quantum != 0:
        raise ValueError(f"ZK leaf quantum {quantum} is not compatible with 8-decimal DVN base unit {DVN_UNIT}. STOP")
    print("Basic amount-unit checks passed; ZK circuit compatibility and issuance still require integration testing.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream_root", type=Path)
    check(parser.parse_args().upstream_root)
