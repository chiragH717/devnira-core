#!/usr/bin/env python3
"""Prepare company treasury genesis allocation from VERIFIED PUBLIC Dilithium ownership.

Two separate operations:
  challenge: issue a fresh address-bound 24h message, no private keys.
  manifest: independently verify signed message + pubkey using pinned native
            DVN binary and create a ONE COMPANY 3M/7M off-chain genesis plan.

Both outputs are OFF-CHAIN. Neither action deploys a genesis, signs a transfer,
creates a custody secret or authorizes mainnet.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from spec.company_treasury import CompanyTreasury, company_genesis_manifest
from spec.verify_company_custody import issue_challenge, verify_company_certificate


def build_signed_company_manifest(certificate: dict, node_binary: Path,
                                  trusted_sha256: str, genesis_time: datetime,
                                  *, now: datetime | None=None) -> dict:
    verification=verify_company_certificate(certificate,node_binary,trusted_sha256,now=now)
    result=company_genesis_manifest(
        genesis_time,
        CompanyTreasury(verification["company_address"], address_verified=True),
    )
    result["company_address_ownership_evidence"]={
        "verifier_sha256":verification["verifier_sha256"],
        "verified_public_address":verification["company_address"],
        "verified_public_key_hex":verification["public_key_hex"],
        "proof_type":"Dilithium87 signed 24-hour genesis challenge",
        "signed_challenge_verified":True,
    }
    result["company_address_verified"]=True
    # A verified signer does not activate Poseidon2 V2 or mint any coins.
    result["production_genesis"]=False
    result["release_blocker"]="Actual V2 runtime, genesis state and live chain tests required"
    return result


def write_fresh(path: Path, data: dict) -> None:
    if path.exists():
        raise FileExistsError("Refusing to overwrite existing public ownership evidence")
    if path.parent != Path(".") and not path.parent.exists():
        raise ValueError("Parent output directory must already exist")
    path.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf-8")


def main():
    parser=argparse.ArgumentParser(description="DEVNIRA public genesis control certificate (no secrets)")
    cmds=parser.add_subparsers(dest="command",required=True)
    ch=cmds.add_parser("challenge")
    ch.add_argument("--company-public-address",required=True)
    ch.add_argument("--output",type=Path,required=True)
    manifest=cmds.add_parser("manifest")
    manifest.add_argument("--signed-public-certificate",type=Path,required=True)
    manifest.add_argument("--trusted-node-binary",type=Path,required=True)
    manifest.add_argument("--trusted-node-sha256",required=True)
    manifest.add_argument("--genesis-utc",required=True,help="YYYY-MM-DDTHH:MM:SS+00:00")
    manifest.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if args.command=="challenge":
        result=issue_challenge(args.company_public_address)
    else:
        cert=json.loads(args.signed_public_certificate.read_text(encoding="utf-8"))
        genesis=datetime.fromisoformat(args.genesis_utc)
        if genesis.tzinfo is None or genesis.utcoffset() is None:
            parser.error("Genesis must be explicit UTC with timezone")
        genesis=genesis.astimezone(timezone.utc)
        if genesis <= datetime.now(timezone.utc):
            parser.error("Actual genesis timestamp must be in the future")
        result=build_signed_company_manifest(
            cert,args.trusted_node_binary,args.trusted_node_sha256,genesis)
    write_fresh(args.output,result)
    print(f"Created public-only {args.command} artifact:",args.output)
    print("NOT A PRODUCTION GENESIS; private seeds and signing keys must remain offline.")


if __name__=="__main__":
    main()
