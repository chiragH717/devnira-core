"""Verify company treasury address ownership using native DEVNIRA Dilithium87.

Requires a *locally installed, trusted, separately verified* DEVNIRA node binary
from the same runtime/protocol revision as the eventual genesis. Only PUBLIC
account, PUBLIC Dilithium key, challenge and signature are accepted.

DO NOT send or commit private keys, mnemonic words, vault unlock passwords or
test-only recovery secrets. Even a verified certificate is NOT proof that the
active ZK/consensus runtime is ready for mainnet.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import secrets
import subprocess

from spec.ss58_company_account import verified_company_public_address, InvalidCompanyAddress

DOMAIN="DEVNIRA-COMPANY-GENESIS-OWNERSHIP-V1"
NETWORK="devnira-mainnet-v1"
HEX64=re.compile(r"^[0-9a-f]{64}$")
HEXBYTES=re.compile(r"^0x[0-9a-fA-F]+$")

class UnverifiedCustody(ValueError):
    pass

def issue_challenge(public_address: str, *, now: datetime | None=None) -> dict:
    try:
        verified_company_public_address(public_address)
    except InvalidCompanyAddress as exc:
        raise UnverifiedCustody("Only a native DEVNIRA SS58 190 company address is allowed") from exc
    supplied=now or datetime.now(timezone.utc)
    if supplied.tzinfo is None or supplied.utcoffset() is None:
        raise UnverifiedCustody("UTC issuance timestamp required")
    stamp=supplied.astimezone(timezone.utc)
    nonce=secrets.token_hex(32)
    expires=stamp + timedelta(hours=24)
    expires_ms=int(expires.timestamp()*1000)
    challenge=f"{DOMAIN}|{NETWORK}|{public_address}|{nonce}|{expires_ms}"
    return {
        "schema":"devnira-company-genesis-custody-challenge-v1",
        "network":NETWORK,
        "company_address":public_address,
        "nonce":nonce,
        "expires_at_utc_ms":expires_ms,
        "message":challenge,
    }

def _run_native(node: Path, *args: str) -> str:
    try:
        response=subprocess.run(
            [str(node), "key", *args],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise UnverifiedCustody("Native DEVNIRA crypto verifier could not execute") from exc
    if response.returncode != 0:
        raise UnverifiedCustody("Native DEVNIRA signature/address verification failed")
    return response.stdout

def verify_company_certificate(certificate: dict, node: Path, expected_node_sha256: str,
                               *, now: datetime | None=None) -> dict:
    if not isinstance(certificate,dict):
        raise UnverifiedCustody("Signed public ownership certificate required")
    if not isinstance(expected_node_sha256,str) or not HEX64.fullmatch(expected_node_sha256):
        raise UnverifiedCustody("Trusted executable SHA256 pin must be lowercase hex")
    node=Path(node)
    try:
        with node.open("rb") as handle:
            digest=hashlib.file_digest(handle,"sha256").hexdigest()
    except OSError as exc:
        raise UnverifiedCustody("Cannot read trusted native DEVNIRA verifier") from exc
    if digest != expected_node_sha256:
        raise UnverifiedCustody("Native verifier binary is not the trusted build")
    addr=certificate.get("company_address")
    try:
        verified_company_public_address(addr)
    except (InvalidCompanyAddress, TypeError) as exc:
        raise UnverifiedCustody("Invalid company SS58 address") from exc
    nonce=certificate.get("nonce")
    expires=certificate.get("expires_at_utc_ms")
    pub=certificate.get("public_key_hex")
    sig=certificate.get("signature_hex")
    if certificate.get("network")!=NETWORK or not isinstance(nonce,str) or not HEX64.fullmatch(nonce):
        raise UnverifiedCustody("Invalid network or challenge nonce")
    if type(expires) is not int or expires<=0:
        raise UnverifiedCustody("Invalid challenge expiry")
    current=now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise UnverifiedCustody("Current time must be timezone aware")
    current_ms=int(current.astimezone(timezone.utc).timestamp()*1000)
    if not (current_ms < expires <= current_ms + 24*60*60*1000):
        raise UnverifiedCustody("Challenge expired or its expiration is too far ahead")
    expected=f"{DOMAIN}|{NETWORK}|{addr}|{nonce}|{expires}"
    if certificate.get("message")!=expected:
        raise UnverifiedCustody("Signed challenge does not match company, nonce and expiry")
    if not isinstance(pub,str) or not HEXBYTES.fullmatch(pub):
        raise UnverifiedCustody("Valid public Dilithium87 key required")
    if not isinstance(sig,str) or not HEXBYTES.fullmatch(sig):
        raise UnverifiedCustody("Valid Dilithium87 signature required")
    _run_native(node,"verify",sig,pub,"--message",expected)
    public_json=_run_native(node,"inspect",pub,"--public","--output-type","json")
    try:
        parsed=json.loads(public_json)
    except (json.JSONDecodeError, TypeError) as exc:
        raise UnverifiedCustody("Native public-key inspection did not return valid JSON") from exc
    if parsed.get("ss58Address")!=addr:
        raise UnverifiedCustody("Signature public key does not derive the proposed company account")
    return {"company_address":addr,"network":NETWORK,
            "public_key_hex":pub,"challenge_verified":True,
            "ownership_signature_verified":True,
            "verifier_sha256":digest}
