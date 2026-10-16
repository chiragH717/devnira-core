#!/usr/bin/env python3
"""Single six-gate DVN release evidence audit. Never deploys or signs anything.

A GREEN development build or self-declared boolean is NEVER production proof.
Even admissible externally signed evidence still needs a human go/no-go and
live infrastructure verification. The default command is report-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from scripts.release_evidence_gate import REQUIRED
from scripts.verify_signed_release_evidence import (
    EvidenceRejected, _read_verified, verify,
)

ROOT = Path(__file__).resolve().parents[1]
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")

# Every pre-existing integration acceptance field is assigned to EXACTLY one
# of the six user-requested engineering streams, without rewriting the
# canonical 9-group signed-release schema or waiving any old requirement.
SIX_GATES = {
    "01_finalized_header_and_history": (
        ("zk_active_proof", ("active_poseidon2_v2", "valid_and_invalid_withdrawal_tests")),
    ),
    "02_active_v2_prover_verifier_settlement": (
        ("zk_active_proof", ("prover_verifier_aggregator_v2",)),
    ),
    "03_independent_8decimal_testnet": (
        ("runtime_genesis", ("native_wasm_dvn_runtime",)),
        ("gpu_testnet", ("two_node_sync", "qpow_mining_rewards", "reorg_and_cap_tests")),
    ),
    "04_company_genesis_treasury": (
        ("runtime_genesis", ("independent_genesis", "genesis_supply_100m_cap",
                             "liquid_3m_locked_7m", "calendar_vesting_enforced")),
    ),
    "05_signed_wallets_and_real_gpu": (
        ("windows_wallet", REQUIRED["windows_wallet"]),
        ("android_wallet", REQUIRED["android_wallet"]),
        ("gpu_testnet", ("nvidia_gpu_proof", "amd_gpu_proof")),
    ),
    "06_pool_explorer_website_audit": tuple(
        (name, REQUIRED[name]) for name in ("pool", "explorer", "website", "operations")
    ),
}
# These security-critical requirements were NOT explicitly distinguishable in
# the older signed release schema. Distinct SHA256 report artifacts must be
# included in and covered by the existing external auditor's Ed25519 signature.
CRITICAL_REPORTS = {
    "01_finalized_header_and_history": (
        "consensus_header_contains_independent_v2_root",
        "historical_witness_finality_reorg_rejects",
    ),
    "02_active_v2_prover_verifier_settlement": (
        "production_vk_matches_native_and_wasm",
        "real_deposit_backed_atomic_spend_and_replay",
    ),
    "03_independent_8decimal_testnet": (
        "same_genesis_two_nodes_signed_transfer",
        "real_reward_supply_and_reorg_integration",
    ),
    "04_company_genesis_treasury": (
        "treasury_public_address_ownership_signature",
        "exact_3m_liquid_7m_cliffs_90m_unminted",
    ),
    "05_signed_wallets_and_real_gpu": (
        "windows_android_signed_send_and_recovery",
        "nvidia_cuda_amd_vulkan_real_gpu_blocks",
    ),
    "06_pool_explorer_website_audit": (
        "real_pool_shares_and_chain_payouts",
        "decoded_finalized_explorer_and_rpc",
        "hostinger_tls_signed_downloads_and_external_audit",
    ),
}

DEPENDENCIES = {
    "01_finalized_header_and_history":
        "Consensus-authenticated independent V2 header roots, historical witnesses and reorg tests",
    "02_active_v2_prover_verifier_settlement":
        "Independent review of domain-bound production fixed keys, native/WASM verifier and atomic replay-safe withdrawals",
    "03_independent_8decimal_testnet":
        "True isolated spendable two-node native/WASM testnet, real transactions and 90M miner budget",
    "04_company_genesis_treasury":
        "Owner-verified SS58-190 treasury PUBLIC address, signed ownership proof and approved UTC genesis time",
    "05_signed_wallets_and_real_gpu":
        "Secure Windows/Android signing and NVIDIA plus AMD physical GPU mining tests",
    "06_pool_explorer_website_audit":
        "Live consensus payouts, decoded public explorer, verified DNS/TLS, audited signed release and independent security audit",
}

def requirement_ids() -> list[str]:
    ids = [group + "." + field for sections in SIX_GATES.values()
           for group, fields in sections for field in fields]
    expected = [group + "." + field for group, fields in REQUIRED.items() for field in fields]
    if sorted(ids) != sorted(expected) or len(ids) != len(set(ids)):
        raise ValueError("Internal six-gate mapping incomplete or duplicates existing release requirements")
    return ids

def _genesis_policy(root: Path) -> tuple[bool, list[str]]:
    try:
        proposal = json.loads((root / "config/genesis-proposal.json").read_text("utf-8"))
    except (ValueError, OSError) as exc:
        return False, ["Approved genesis proposal is missing or malformed"]
    errors = []
    expected = {
        "base_units_per_coin": 100_000_000,
        "max_supply_units": 10_000_000_000_000_000,
        "mining_allocation_units": 9_000_000_000_000_000,
        "premine_units": 1_000_000_000_000_000,
    }
    for name, number in expected.items():
        if type(proposal.get(name)) is not int or proposal[name] != number:
            errors.append("Genesis economy mismatch: " + name)
    company = proposal.get("company_treasury", {})
    if not isinstance(company, dict):
        company = {}
    if company.get("instant_units") != 300_000_000_000_000:
        errors.append("Treasury missing exact 3M liquid allocation")
    if company.get("locked_units") != 700_000_000_000_000:
        errors.append("Treasury missing exact 7M locked allocation")
    if company.get("monthly_unlock_count") != 12:
        errors.append("Treasury vesting must use twelve calendar cliffs")
    address = company.get("public_address")
    if not isinstance(address, str) or not address.strip():
        errors.append("Owner-verified public treasury address still absent")
    stamp = proposal.get("genesis_timestamp_ms")
    if type(stamp) is not int or stamp <= 0:
        errors.append("Owner-approved UTC Genesis time still absent")
    return not errors, errors

def snapshot(root: Path, revision: str) -> dict:
    requirement_ids()
    if not SHA40.fullmatch(revision):
        raise ValueError("Git revision must be a 40-character lowercase Git commit SHA")
    root = Path(root)
    genesis_valid, genesis_errors = _genesis_policy(root)
    gates = {
        name: {
            "status": "BLOCKED",
            "evidence_admitted": False,
            "required_signed_fields": [a+"."+f for a, fields in sections for f in fields],
            "additional_signed_sha256_reports": list(CRITICAL_REPORTS[name]),
            "next_dependency": DEPENDENCIES[name],
        }
        for name, sections in SIX_GATES.items()
    }
    blockers = list(genesis_errors)
    evidence_file = root / "config/release-evidence.json"
    auditors_file = root / "config/trusted-release-auditors.json"
    auditor_ids: list[str] = []
    if not evidence_file.exists():
        blockers.append("Real signed release evidence manifest is missing")
    if not auditors_file.exists():
        blockers.append("Approved independent auditor registry is missing")
    else:
        try:
            auditors = json.loads(auditors_file.read_text("utf-8"))
            auditor_ids = [a["key_id"] for a in auditors.get("approved_ed25519_auditors", [])
                           if isinstance(a, dict) and isinstance(a.get("key_id"), str)]
            if not auditor_ids:
                blockers.append("No independently approved auditor public signing key")
        except (OSError, ValueError, AttributeError, TypeError):
            blockers.append("Independent auditor registry invalid")
            auditors = {}
    evidence_verified = False
    if evidence_file.exists():
        try:
            evidence = json.loads(evidence_file.read_text("utf-8"))
            if not auditors_file.exists():
                raise EvidenceRejected("Auditor registry absent")
            verify(evidence, auditors, root / "evidence/production")
            if evidence.get("git_revision") != revision:
                raise EvidenceRejected("Signed evidence commit differs from exact current revision")
            if not genesis_valid:
                raise EvidenceRejected("Owner-approved treasury genesis inputs missing or inconsistent")
            extras = evidence.get("critical_acceptance_evidence")
            necessary = {key for fields in CRITICAL_REPORTS.values() for key in fields}
            if not isinstance(extras, dict) or set(extras) != necessary:
                raise EvidenceRejected("13 additional independent-root, settlement and hardware reports required")
            digests: set[str] = set()
            for key, claim in sorted(extras.items()):
                if not isinstance(claim, dict) or set(claim) != {"file", "sha256"}:
                    raise EvidenceRejected("Missing SHA256-pinned critical evidence for " + key)
                digest = claim["sha256"]
                if not isinstance(digest, str) or not SHA64.fullmatch(digest):
                    raise EvidenceRejected("Malformed critical report digest for " + key)
                # Same safe path restrictions and SHA256 verification as the
                # existing cryptographically signed release gate.
                data = _read_verified(root / "evidence/production", claim["file"], digest)
                if not data:
                    raise EvidenceRejected("Empty critical report")
                digests.add(digest)
            if len(digests) != len(necessary):
                raise EvidenceRejected("Independent critical requirements cannot share a single report hash")
            evidence_verified = True
        except (OSError, ValueError, EvidenceRejected) as exc:
            blockers.append("Signed production evidence rejected: " + str(exc))
    if evidence_verified:
        for gate in gates.values():
            gate["status"] = "SIGNED_EVIDENCE_ADMITTED_REQUIRES_HUMAN_GO_NO_GO"
            gate["evidence_admitted"] = True
    return {
        "schema": "devnira-mainnet-six-gate-evidence-snapshot-v1",
        "revision": revision,
        "chain": "DEVNIRA",
        "network": "NOT DEPLOYED BY THIS REPORT",
        "mainnet_deployed": False,
        "signed_release_evidence_admitted": evidence_verified,
        "eligible_for_manual_release_review": evidence_verified and genesis_valid,
        "genesis_policy_inputs_complete": genesis_valid,
        "gate_count": 6,
        "gates": gates,
        "blocking_conditions": blockers,
        "note": "PASS of the diagnostic CI means the report ran, never that DVN mainnet passed. Signed claims still need independent inspection and explicit release authorization.",
    }

def markdown(report: dict) -> str:
    lines = [
        "# DEVNIRA mainnet release — six-gate evidence snapshot",
        "",
        "Network: **NOT DEPLOYED BY THIS REPORT**",
        "Signed production evidence: **" + ("ADMITTED FOR MANUAL REVIEW" if report["signed_release_evidence_admitted"] else "BLOCKED") + "**",
        "",
        "| Gate | Admission |",
        "|---|---|",
    ]
    for gate, item in report["gates"].items():
        lines.append("| " + gate + " | " + item["status"] + " |")
    lines += ["", "## Blocking conditions", ""]
    lines += ["- " + x.replace("|", "/") for x in report["blocking_conditions"]]
    lines += ["", "## External prerequisites", ""]
    lines += ["- " + item["next_dependency"] for item in report["gates"].values()]
    lines.append("\nNot a mainnet launch approval.\n")
    return "\n".join(lines)

def main() -> None:
    p = argparse.ArgumentParser(description="One-command 6-track DEVNIRA production evidence snapshot; NO SEND")
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--revision", required=True, help="Exact source commit SHA under review")
    p.add_argument("--json-out", type=Path)
    p.add_argument("--markdown-out", type=Path)
    p.add_argument("--require-evidence", action="store_true", help="Fail when independent signed evidence is not admissible")
    args = p.parse_args()
    report = snapshot(args.root, args.revision)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.markdown_out:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(markdown(report), encoding="utf-8")
    print(json.dumps({"six_gates": {g: v["status"] for g, v in report["gates"].items()},
                      "signed_evidence_admitted": report["signed_release_evidence_admitted"],
                      "mainnet_deployed": False}, sort_keys=True))
    if args.require_evidence and not report["eligible_for_manual_release_review"]:
        p.exit(1, "STOP: DEVNIRA six-gate production evidence BLOCKED. No mainnet Send or deployment.\n")

if __name__ == "__main__":
    main()
