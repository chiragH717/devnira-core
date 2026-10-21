#!/usr/bin/env python3
"""MANUAL only: final acceptance orchestration. Never a mainnet launcher."""
import argparse
import os
import subprocess
import sys

REQUIRED=("DVN_TRUSTED_DEV_GENESIS","DVN_TEST_FROM_SS58",
"DVN_TEST_TO_SS58","DVN_TEST_AMOUNT_UNITS","DVN_DEV_MAX_FEE_UNITS",
"DVN_SIGNED_DEV_EXTRINSIC","DVN_V2_FINALIZED_HEIGHT",
"DVN_PRODUCTION_REVISION")
def invoke(args):
    print("FINAL integration:",args[0],args[1],flush=True)
    subprocess.run(args,check=True)
def main():
    p=argparse.ArgumentParser(description="One MANUAL run only, blocked by missing real evidence")
    p.add_argument("--run",action="store_true",help="Explicit authorization to execute final tests")
    x=p.parse_args()
    missing=[name for name in REQUIRED if not os.environ.get(name)]
    if not x.run:
        print("STAGED — NOT RUN. Required public-only environment:",", ".join(REQUIRED))
        print("Inactive V2 header mode, unapproved VK, missing physical mining remain blockers.")
        return
    if missing:
        p.exit(2,"STOP missing external evidence: "+", ".join(missing)+"\n")
    py=sys.executable;e=os.environ
    invoke([py,"-m","unittest","discover","-s","tests",
            "-p","test_final_batch_new_boundaries.py","-v"])
    invoke([py,"-m","scripts.dvn_unsigned_dev_signing_intent",
            "--trusted-genesis",e["DVN_TRUSTED_DEV_GENESIS"],
            "--from-public",e["DVN_TEST_FROM_SS58"],
            "--to-public",e["DVN_TEST_TO_SS58"],
            "--amount-units",e["DVN_TEST_AMOUNT_UNITS"],
            "--max-fee-units",e["DVN_DEV_MAX_FEE_UNITS"],
            "--json-out","/tmp/dvn-unsigned-intent.json"])
    invoke([py,"-m","scripts.dvn_v2_consensus_root_probe",
            "--trusted-genesis",e["DVN_TRUSTED_DEV_GENESIS"],
            "--height",e["DVN_V2_FINALIZED_HEIGHT"],
            "--json-out","/tmp/dvn-v2-header-root-proof.json"])
    invoke([py,"-m","scripts.dvn_signed_transfer_acceptance",
            "--trusted-genesis",e["DVN_TRUSTED_DEV_GENESIS"],
            "--from-public",e["DVN_TEST_FROM_SS58"],
            "--to-public",e["DVN_TEST_TO_SS58"],
            "--amount-units",e["DVN_TEST_AMOUNT_UNITS"],
            "--signed-extrinsic-file",e["DVN_SIGNED_DEV_EXTRINSIC"],
            "--json-out","/tmp/dvn-real-dev-transfer.json"])
    invoke([py,"-m","scripts.dvn_physical_gpu_probe",
            "--require-nvidia","--require-amd",
            "--json-out","/tmp/dvn-physical-gpus.json"])
    invoke([py,"-m","scripts.six_gate_release_snapshot",
            "--revision",e["DVN_PRODUCTION_REVISION"],
            "--require-evidence","--json-out","/tmp/dvn-final-release.json"])
    print("Manual gates finished; independent production audit still required.")
if __name__=="__main__":main()
