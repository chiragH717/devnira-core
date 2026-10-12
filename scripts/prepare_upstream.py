#!/usr/bin/env python3
"""Prepare an isolated DEVNIRA development chain-spec candidate from a Quantus checkout.
NOT a finished independent runtime or zero-premine genesis.
"""
import argparse
from pathlib import Path

def patch(root: Path):
    path = root / "node/src/chain_spec.rs"
    source = path.read_text()
    start = source.index("pub fn development_chain_spec()")
    end = source.index("\n/// Heisenberg", start)
    dev = source[start:end]
    expected = ['json!(12)', 'json!("DEV")', 'json!(189)', '.with_id("dev")', '.with_protocol_id("quantus-devnet")', 'Quantus DevNet']
    for needle in expected:
        if needle not in dev:
            raise RuntimeError(f"Upstream changed, manual review required: {needle}")
    dev = (dev.replace('json!(12)', 'json!(8)')
           .replace('json!("DEV")', 'json!("DVN")')
           .replace('json!(189)', 'json!(190)')
           .replace('.with_id("dev")', '.with_id("devnira-local")')
           .replace('.with_protocol_id("quantus-devnet")', '.with_protocol_id("devnira-local-v1")')
           .replace('Quantus DevNet', 'DEVNIRA Local'))
    # Preserve entry-point function name, so upstream CLI can still call it.
    source = source[:start] + dev + source[end:]
    path.write_text(source)
    print("Patched local dev chain-spec metadata and network identity.")
    print("WARNING: Upstream development genesis may have premine. NOT mainnet-ready.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("upstream_root", type=Path)
    patch(ap.parse_args().upstream_root)
