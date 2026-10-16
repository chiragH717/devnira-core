#!/usr/bin/env python3
"""Fail-closed development PRIVATE/PUBLIC verifier-only AND common byte pins; no Send."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat

CONFIG=Path(__file__).resolve().parents[1]/"config/dvn-v2-dev-vk-fingerprints.json"
PINS=Path(__file__).resolve().parents[1]/"config/upstream-pins.json"
KEY_FILES=("private-v2-24pi-vk.bin","private-v2-24pi-common.bin",
           "public-v2-50pi-vk.bin","public-v2-50pi-common.bin")
SHA256=re.compile(r"[0-9a-f]{64}\Z")
MAX_BYTES=8*1024*1024

class V2FingerprintRejected(ValueError):
    pass

def verify_development_vk(artifacts:Path, *, config:Path=CONFIG, pins:Path=PINS)->dict:
    try:
        policy=json.loads(Path(config).read_text(encoding="utf-8"))
        upstream=json.loads(Path(pins).read_text(encoding="utf-8"))
    except (OSError,ValueError) as exc:
        raise V2FingerprintRejected("Missing/malformed local verifier configuration") from exc
    if policy.get("schema")!="devnira-v2-development-verifier-fingerprint-v1":
        raise V2FingerprintRejected("Wrong verifier fingerprint schema")
    if set(policy.get("sha256",{}))!=set(KEY_FILES):
        raise V2FingerprintRejected("Both tier verifier AND common data are mandatory")
    if policy.get("public_inputs")!={"private":24,"public":50} or policy.get("rust_version")!="1.93.0":
        raise V2FingerprintRejected("Wrong circuit ABI or toolchain")
    if (policy.get("circuit_pin")!=upstream.get("zk_circuits",{}).get("sha") or
        policy.get("chain_pin")!=upstream.get("upstream_chain",{}).get("sha")):
        raise V2FingerprintRejected("Wrong upstream source pins")
    if any(policy.get(k) is not False for k in
           ("production_vk_approved","runtime_vk_embedded","deposit_backing_verified","release_allowed")):
        raise V2FingerprintRejected("Development key is NOT production approval")
    if "DEVELOPMENT-ONLY" not in str(policy.get("classification","")):
        raise V2FingerprintRejected("Development-only warning missing")
    root=Path(artifacts)
    if root.is_symlink() or not root.is_dir():
        raise V2FingerprintRejected("Artifact directory missing or symlinked")
    checked={}
    for name in KEY_FILES:
        expected=policy["sha256"][name]
        if not isinstance(expected,str) or not SHA256.fullmatch(expected):
            raise V2FingerprintRejected("Malformed trusted digest: "+name)
        artifact=root/name
        if artifact.is_symlink():
            raise V2FingerprintRejected("Symlinked key: "+name)
        try:
            meta=artifact.stat(follow_symlinks=False)
            if not stat.S_ISREG(meta.st_mode) or not 0<meta.st_size<=MAX_BYTES:
                raise V2FingerprintRejected("Empty/nonregular/oversized key: "+name)
            with artifact.open("rb") as f:
                actual=hashlib.file_digest(f,"sha256").hexdigest()
        except OSError as exc:
            raise V2FingerprintRejected("Missing/unreadable key: "+name) from exc
        if actual!=expected:
            raise V2FingerprintRejected("V2 DEVELOPMENT VERIFIER DRIFT: "+name)
        checked[name]=actual
    return {"classification":"DEVELOPMENT-ONLY, NOT PRODUCTION",
            "keys_and_common_data_verified":len(checked),"sha256":checked,
            "production_vk_approved":False,"runtime_activated":False,
            "deposit_backing_verified":False,"release_allowed":False}

def main():
    ap=argparse.ArgumentParser(description="Verify development V2 fixed SHA256 bytes, not approved production keys")
    ap.add_argument("artifact_directory",type=Path)
    args=ap.parse_args()
    try:
        print(json.dumps(verify_development_vk(args.artifact_directory),sort_keys=True))
    except V2FingerprintRejected as exc:
        ap.exit(1,"STOP: "+str(exc)+"\n")

if __name__=="__main__":
    main()
