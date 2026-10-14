#!/usr/bin/env python3
"""Stage PUBLIC DVN treasury owner offline without handling wallet secrets.

Run ONLY on a computer with an independently trusted DEVNIRA native verifier.
Requires a public certificate signed with a key created/held on the OWNER'S
own secure device. Refuses to stage files inside the public git repository.
"""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from spec.approved_company_genesis import stage_verified_company_genesis

def create_bundle_files(bundle: dict, output_dir: Path) -> None:
    output_dir = output_dir.expanduser().resolve()
    if output_dir == ROOT or ROOT in output_dir.parents:
        raise ValueError("STOP: company genesis review outputs must be OUTSIDE public Git repository")
    if not output_dir.parent.is_dir():
        raise ValueError("Parent folder must exist; no implicit recursive creation")
    # An exclusive directory avoids silently overwriting earlier owner
    # approvals. Owner controls sharing of PUBLIC-but-sensitive prelaunch
    # account and launch-time information.
    output_dir.mkdir(mode=0o700,exist_ok=False)
    files={
        "public-company-ownership-evidence.json": bundle["company_ownership"],
        "proposed-genesis-reviewed-NOT-LIVE.json": bundle["approved_offchain_proposal"],
        "checked-genesis-inputs-NOT-LIVE.json": bundle["checked_genesis_inputs"],
    }
    for name,data in files.items():
        path=output_dir/name
        flags=os.O_CREAT|os.O_EXCL|os.O_WRONLY
        fd=os.open(str(path),flags,0o600)
        with os.fdopen(fd,"w",encoding="utf-8") as stream:
            json.dump(data,stream,indent=2,sort_keys=True)
            stream.write("\n")

def main():
    ap=argparse.ArgumentParser(description="DEVNIRA company public ownership -> OFFCHAIN genesis input review")
    ap.add_argument("--certificate",type=Path,required=True)
    ap.add_argument("--trusted-node",type=Path,required=True)
    ap.add_argument("--trusted-node-sha256",required=True)
    ap.add_argument("--approved-proposal",type=Path,default=ROOT/"config/genesis-proposal.json")
    ap.add_argument("--genesis-utc",required=True,help="future ISO-8601 date with timezone")
    ap.add_argument("--output-dir",type=Path,required=True,help="new folder OUTSIDE public repo")
    args=ap.parse_args()
    genesis=datetime.fromisoformat(args.genesis_utc)
    cert=json.loads(args.certificate.read_text(encoding="utf-8"))
    proposal=json.loads(args.approved_proposal.read_text(encoding="utf-8"))
    result=stage_verified_company_genesis(
        proposal,cert,args.trusted_node,args.trusted_node_sha256,genesis)
    create_bundle_files(result,args.output_dir)
    print("PASS: public Dilithium87 signing owner verified; review artifacts staged OUTSIDE Git.")
    print("NOT A LIVE GENESIS: independent native/WASM V2 settlement and audits still required.")

if __name__=="__main__":
    main()
