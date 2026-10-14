"""Locally stage a company-controlled public DVN account for genesis review.

Requires REAL native Dilithium87 signed public ownership certificate verified
against an explicitly SHA256-pinned node binary. No secret phrase or new wallet
key is ever created by this module. Results remain OFF-CHAIN development-only.
"""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from spec.genesis_candidate import construct_inputs
from spec.verify_company_custody import verify_company_certificate

class GenesisApprovalError(ValueError):
    pass

def stage_verified_company_genesis(
    proposal: dict, certificate: dict, trusted_node: Path,
    trusted_sha256: str, genesis_utc: datetime, *, now: datetime | None = None,
) -> dict:
    moment = now or datetime.now(timezone.utc)
    if (moment.tzinfo is None or moment.utcoffset() is None
            or genesis_utc.tzinfo is None or genesis_utc.utcoffset() is None):
        raise GenesisApprovalError("Explicit timezone-aware UTC dates required")
    moment = moment.astimezone(timezone.utc)
    genesis_utc = genesis_utc.astimezone(timezone.utc)
    if genesis_utc <= moment:
        raise GenesisApprovalError("Launch timestamp must be future, independently approved UTC")
    if not isinstance(proposal, dict):
        raise GenesisApprovalError("Approved supply proposal JSON required")

    # The native signature AND full Dilithium public key are checked against
    # the exact SS58-190 beneficiary, challenge, network, nonce and expiry.
    verified = verify_company_certificate(
        certificate, trusted_node, trusted_sha256, now=moment)
    if verified.get("ownership_signature_verified") is not True:
        raise GenesisApprovalError("Native public ownership signature unverified")
    public_address = verified["company_address"]
    working = deepcopy(proposal)
    treasury = working.get("company_treasury")
    if not isinstance(treasury, dict):
        raise GenesisApprovalError("Approved company treasury configuration missing")
    if treasury.get("public_address") not in (None, public_address):
        raise GenesisApprovalError("Refusing silent change of approved company beneficiary")
    current = working.get("genesis_timestamp_ms")
    ms = int(genesis_utc.timestamp() * 1000)
    if current not in (None, ms):
        raise GenesisApprovalError("Refusing silent change of approved genesis timestamp")
    if ms <= int(moment.timestamp() * 1000):
        raise GenesisApprovalError("Launch must be in the future")
    treasury["public_address"] = public_address
    treasury["public_address_status"] = "signed_native_dilithium87_ownership_verified_offchain_only"
    working["genesis_timestamp_ms"] = ms
    working["allocation_status"] = "verified_public_company_owner_offchain_genesis_pending"
    vest = working.get("team_investor_founder_vesting")
    if not isinstance(vest, dict):
        raise GenesisApprovalError("Vesting policy missing")
    current_beneficiaries = vest.get("beneficiary_addresses")
    if current_beneficiaries not in ([], [public_address]):
        raise GenesisApprovalError("Refusing extra or conflicting vesting beneficiaries")
    vest["beneficiary_addresses"] = [public_address]
    vest["status"] = "offchain_company_public_owner_verified_not_activated"
    # Guard against drift in ANY approved supply, old premine or schedule.
    approved_inputs = construct_inputs(working)
    # Do not allow a signed challenge to be confused with chain activation.
    assert approved_inputs["runnable_chain_spec"] is False
    return {
        "schema": "devnira-company-genesis-staged-review-bundle-v1",
        "production_genesis": False,
        "network_live": False,
        "company_ownership": {
            "company_public_address": public_address,
            "full_public_key_hex": verified["public_key_hex"],
            "signed_challenge_verified_with_native_dilithium87": True,
            "trusted_verifier_sha256": verified["verifier_sha256"],
            "private_keys_ever_included": False,
        },
        "approved_offchain_proposal": working,
        "checked_genesis_inputs": approved_inputs,
        "remaining_consensus_requirements": [
            "active V2 root-authenticated and nullifier-protected prover/aggregator/verifier",
            "matching independent eight-decimal FRAME native plus WASM runtime",
            "12 Gregorian cliff immutable on-chain vesting and miner-only 90M cap",
            "unique checked live chain spec, measured issuance and genesis hash",
            "two-node and real GPU settlement/security acceptance",
        ],
    }
