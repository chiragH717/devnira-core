#!/usr/bin/env python3
"""Verify auditor-signed and digest-pinned DEVNIRA mainnet evidence (not a security audit).

Only the protected repository's preapproved public Ed25519 auditor keys are
trusted. A user-supplied signature/key or green development tests cannot
authorize production. No auditor is preapproved: production FAILS CLOSED.
"""
from __future__ import annotations
import argparse
import base64
import binascii
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
from scripts.release_evidence_gate import REQUIRED, audit

SHA = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
AUDITOR_ID = re.compile(r"[a-z0-9][a-z0-9_.-]{2,63}\Z")
MAX_FILE_BYTES = 32 * 1024 * 1024

class EvidenceRejected(ValueError):
    pass

def canonical_claim(evidence: dict) -> bytes:
    signed = {k: v for k, v in evidence.items() if k != "auditor_attestation"}
    return json.dumps(signed, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")

def _read_verified(root: Path, path: str, expected_hash: str) -> bytes:
    if not isinstance(path, str) or len(path) > 160 or "\\" in path:
        raise EvidenceRejected("Invalid evidence path")
    rel = Path(path)
    if rel.is_absolute() or not rel.parts or any(p.startswith(".") for p in rel.parts):
        raise EvidenceRejected("Evidence path traversal is forbidden")
    try:
        root = root.resolve(strict=True)
        node = root
        for part in rel.parts:
            node = node / part
            if node.is_symlink():
                raise EvidenceRejected("Symlink in evidence path")
        if not node.resolve(strict=True).is_relative_to(root):
            raise EvidenceRejected("Evidence path escapes protected root")
        if not node.is_file() or not 0 < node.stat().st_size <= MAX_FILE_BYTES:
            raise EvidenceRejected("Evidence file empty, missing or oversized")
        data = node.read_bytes()
    except (OSError, RuntimeError) as exc:
        raise EvidenceRejected("Cannot safely read evidence artifact") from exc
    if hashlib.sha256(data).hexdigest() != expected_hash:
        raise EvidenceRejected("SHA256 evidence mismatch")
    return data

def verify(evidence: dict, auditors: dict, artifact_root: Path) -> dict:
    if not isinstance(evidence, dict) or not isinstance(auditors, dict):
        raise EvidenceRejected("Release evidence and auditor trust config must be objects")
    missing = audit(evidence)
    if missing:
        raise EvidenceRejected("Release checklist not complete: " + missing[0])
    revision = evidence.get("git_revision")
    if not isinstance(revision, str) or COMMIT.fullmatch(revision) is None:
        raise EvidenceRejected("Production source must be pinned to a 40-char lowercase commit")
    mapping = evidence.get("artifact_evidence")
    expected = {g+"."+f for g, fields in REQUIRED.items() for f in fields}
    if not isinstance(mapping, dict) or set(mapping) != expected:
        raise EvidenceRejected("Each production gate needs one SHA256-pinned artifact")
    digests = set()
    for gate, claim in sorted(mapping.items()):
        if not isinstance(claim, dict) or set(claim) != {"file", "sha256"}:
            raise EvidenceRejected("Malformed artifact reference for "+gate)
        digest = claim.get("sha256")
        if not isinstance(digest, str) or SHA.fullmatch(digest) is None:
            raise EvidenceRejected("Malformed artifact digest for "+gate)
        _read_verified(artifact_root, claim.get("file"), digest)
        digests.add(digest)
    if len(digests) < len(REQUIRED):
        raise EvidenceRejected("Each product area needs separately inspectable reports")
    allowlist = auditors.get("approved_ed25519_auditors")
    if not isinstance(allowlist, list) or not allowlist:
        raise EvidenceRejected("No independent auditor publicly approved — release blocked")
    att = evidence.get("auditor_attestation")
    if not isinstance(att, dict) or set(att) != {"key_id", "signature_base64"}:
        raise EvidenceRejected("Independent detached audit signature required")
    key_id = att["key_id"]
    if not isinstance(key_id, str) or AUDITOR_ID.fullmatch(key_id) is None:
        raise EvidenceRejected("Malformed auditor identity")
    accepted = [a for a in allowlist if isinstance(a, dict) and a.get("key_id") == key_id]
    if len(accepted) != 1 or set(accepted[0]) != {"key_id", "public_key_pem"}:
        raise EvidenceRejected("Auditor public key is not uniquely trusted")
    pem = accepted[0]["public_key_pem"]
    if not isinstance(pem, str) or not pem.startswith("-----BEGIN PUBLIC KEY-----\n") or len(pem) > 2000:
        raise EvidenceRejected("Malformed approved auditor public key")
    try:
        sig = base64.b64decode(att["signature_base64"], validate=True)
    except (ValueError, TypeError, binascii.Error) as exc:
        raise EvidenceRejected("Invalid independent auditor signature encoding") from exc
    if len(sig) != 64:
        raise EvidenceRejected("Ed25519 signature must be exactly 64 bytes")
    with tempfile.TemporaryDirectory() as dirname:
        d = Path(dirname)
        (d / "pub.pem").write_text(pem, encoding="ascii")
        (d / "payload").write_bytes(canonical_claim(evidence))
        (d / "signature").write_bytes(sig)
        try:
            result = subprocess.run(["openssl", "pkeyutl", "-verify", "-rawin",
                                     "-pubin", "-inkey", str(d/"pub.pem"),
                                     "-in", str(d/"payload"),
                                     "-sigfile", str(d/"signature")],
                                    check=False, capture_output=True, timeout=20)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise EvidenceRejected("Auditor signature verifier unavailable") from exc
    if result.returncode != 0:
        raise EvidenceRejected("Trusted auditor did NOT sign exactly these release claims")
    return {"signed_manifest_verified": True, "auditor_key_id": key_id,
            "git_revision": revision, "genesis_hash": evidence["genesis_hash"],
            "gate_count": len(expected), "note":
            "Signature authenticates claims and checksums; real independent audit still required"}

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("evidence", type=Path)
    p.add_argument("--auditors", type=Path, default=Path("config/trusted-release-auditors.json"))
    p.add_argument("--artifact-root", type=Path, default=Path("evidence/production"))
    args = p.parse_args()
    try:
        result = verify(json.loads(args.evidence.read_text("utf-8")),
                        json.loads(args.auditors.read_text("utf-8")), args.artifact_root)
    except (OSError, ValueError) as exc:
        p.exit(1, "MAINNET BLOCKED: " + str(exc) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    print("The signature does not by itself independently verify network safety.")

if __name__ == "__main__":
    main()
