#!/usr/bin/env python3
"""Build a deterministic OFF-CHAIN DVN genesis input plan with no fake address.

Never produce or publish a mainnet chain-spec from this command. Missing
company public custody address or approved genesis timestamp is fatal.
"""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from spec.genesis_candidate import construct_inputs, GenesisInputError

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--proposal",type=Path,default=Path("config/genesis-proposal.json"))
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if a.output.resolve()==a.proposal.resolve():
        p.error("Refusing to overwrite approved genesis proposal")
    try:
        payload=construct_inputs(json.loads(a.proposal.read_text(encoding="utf-8")))
    except (GenesisInputError, ValueError, KeyError) as exc:
        p.error(f"Genesis not ready: {exc}")
    a.output.write_text(json.dumps(payload,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("Written OFF-CHAIN checked genesis inputs only. NOT a blockchain launch.")

if __name__=="__main__":
    main()
