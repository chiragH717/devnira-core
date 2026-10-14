#!/usr/bin/env python3
"""Auditable DEVNIRA project state from checked-in sources (not a success claim).

No source file, green reference test or UI label can itself prove that a
production blockchain is deployed. Missing release evidence is shown explicitly.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def status(root: Path=ROOT) -> dict:
    proposal=json.loads((root/"config/genesis-proposal.json").read_text())
    c=proposal["company_treasury"]
    problems=[]
    if proposal["base_units_per_coin"]!=100_000_000:
        problems.append("Token base-unit configuration differs from 8 decimals")
    if proposal["max_supply_units"]!=10_000_000_000_000_000:
        problems.append("Total issuance does not equal 100M DVN")
    if proposal["mining_allocation_units"]!=9_000_000_000_000_000:
        problems.append("Mining budget does not equal 90M DVN")
    if c["instant_units"]!=300_000_000_000_000 or c["locked_units"]!=700_000_000_000_000:
        problems.append("Founder liquid/vesting split differs from approved 3M/7M")
    if c.get("public_address") is None:
        problems.append("Verified company DEVNIRA public address not available")
    problems.extend([
        "Active V2 Poseidon2 leaf, aggregator, prover and verifier not integrated end-to-end",
        "Independent 8-decimal DEVNIRA mainnet genesis has not been generated and tested",
        "Vesting pot existential-deposit fix is opt-in FRAME code only; actual independent DVN genesis remains unbuilt/unverified",
        "Windows secure transaction-signing wallet has not passed end-to-end tests",
        "Two live DVN nodes with NVIDIA and AMD GPU QPoW miners not validated",
        "Source revisions pinned for development; independent full-runtime build and security review incomplete",
    ])
    jobs=["ZK prototype codec/amount gadget","Reward and vesting on upstream development runtime",
          "Windows read-only node monitor","GPU readiness/reference audits"]
    return {
        "project":"DEVNIRA", "symbol":"DVN",
        "network":"NOT MAINNET READY",
        "company_treasury_policy":"one company-owned account; actual public address pending",
        "approved_supply": {
            "max_DVN":100_000_000,
            "mined_DVN":90_000_000,
            "liquid_company_DVN":3_000_000,
            "twelve_month_company_locked_DVN":7_000_000,
        },
        "last_user_verified_candidate_build":"four-component integration build #3; development only",
        "candidate_jobs_passed":jobs,
        "known_blockers":problems,
        "economics_configuration_valid":not any("configuration" in p or "issuance" in p and "does not" in p or "budget" in p or "split" in p for p in problems),
    }

if __name__=="__main__":
    print(json.dumps(status(), indent=2))
