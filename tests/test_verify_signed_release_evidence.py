"""Test-only temporary Ed25519 auditor identities: NEVER real DVN custody keys."""
import base64
import copy
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.release_evidence_gate import REQUIRED
from scripts.verify_signed_release_evidence import (
    EvidenceRejected, canonical_claim, verify,
)

class SignedProductionEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.root = self.home / "reports"
        self.root.mkdir()
        self.manifest = {
            "network": "devnira-independent",
            "genesis_hash": "0x" + "a" * 64,
            "git_revision": "b" * 40,
            "artifact_evidence": {},
        }
        for group, fields in REQUIRED.items():
            self.manifest[group] = {field: True for field in fields}
            for field in fields:
                ident = f"{group}.{field}"
                value = ("SYNTHETIC TEST FIXTURE / NO LIVE CHAIN: " + ident).encode()
                file = self.root / (ident + ".txt")
                file.write_bytes(value)
                self.manifest["artifact_evidence"][ident] = {
                    "file": file.name, "sha256": hashlib.sha256(value).hexdigest()
                }
        self.private = self.home/"temporary-test-only.key"
        self.public = self.home/"temporary-test-only.pem"
        subprocess.run(["openssl","genpkey","-algorithm","ed25519",
                        "-out",str(self.private)],check=True,capture_output=True)
        subprocess.run(["openssl","pkey","-in",str(self.private),"-pubout",
                        "-out",str(self.public)],check=True,capture_output=True)
        self.auditors = {"approved_ed25519_auditors":[
            {"key_id":"unit-test-only", "public_key_pem":self.public.read_text()}
        ]}
        self.sign()

    def sign(self):
        self.manifest.pop("auditor_attestation",None)
        payload=self.home/"to-sign.json"
        signature=self.home/"signature"
        payload.write_bytes(canonical_claim(self.manifest))
        subprocess.run(["openssl","pkeyutl","-sign","-rawin","-inkey",
                        str(self.private),"-in",str(payload),"-out",str(signature)],
                       check=True,capture_output=True)
        self.manifest["auditor_attestation"]={
            "key_id":"unit-test-only",
            "signature_base64":base64.b64encode(signature.read_bytes()).decode("ascii"),
        }

    def test_valid_ephemeral_test_fixture_only(self):
        result=verify(self.manifest,self.auditors,self.root)
        self.assertTrue(result["signed_manifest_verified"])
        self.assertEqual(result["gate_count"],sum(len(x) for x in REQUIRED.values()))

    def test_prod_unapproved_auditor_fails_closed(self):
        with self.assertRaisesRegex(EvidenceRejected,"No independent auditor"):
            verify(self.manifest,{"approved_ed25519_auditors":[]},self.root)

    def test_modifying_genesis_or_commit_invalidates_signature(self):
        for key,value in [("genesis_hash","0x"+"c"*64),("git_revision","d"*40)]:
            changed=copy.deepcopy(self.manifest)
            changed[key]=value
            with self.subTest(key=key),self.assertRaisesRegex(EvidenceRejected,"did NOT sign"):
                verify(changed,self.auditors,self.root)

    def test_boolean_labels_are_not_signatures(self):
        changed=copy.deepcopy(self.manifest)
        changed["zk_active_proof"]["active_poseidon2_v2"]=False
        with self.assertRaisesRegex(EvidenceRejected,"checklist not complete"):
            verify(changed,self.auditors,self.root)
        changed["zk_active_proof"]["active_poseidon2_v2"]="true"
        with self.assertRaisesRegex(EvidenceRejected,"checklist not complete"):
            verify(changed,self.auditors,self.root)

    def test_missing_and_modified_report_fail(self):
        name=next(iter(self.manifest["artifact_evidence"]))
        changed=copy.deepcopy(self.manifest)
        changed["artifact_evidence"].pop(name)
        with self.assertRaisesRegex(EvidenceRejected,"Each production gate"):
            verify(changed,self.auditors,self.root)
        report=self.root/self.manifest["artifact_evidence"][name]["file"]
        report.write_bytes(report.read_bytes()+b"FORGED")
        with self.assertRaisesRegex(EvidenceRejected,"SHA256 evidence mismatch"):
            verify(self.manifest,self.auditors,self.root)

    def test_symlink_escape_and_path_traversal_rejected(self):
        name=next(iter(self.manifest["artifact_evidence"]))
        for candidate in ["../../secrets","/etc/passwd","..\\wrong"]:
            manifest=copy.deepcopy(self.manifest)
            manifest["artifact_evidence"][name]["file"]=candidate
            with self.subTest(path=candidate),self.assertRaises(EvidenceRejected):
                verify(manifest,self.auditors,self.root)
        good=self.root/self.manifest["artifact_evidence"][name]["file"]
        (self.root/"link").symlink_to(good)
        changed=copy.deepcopy(self.manifest)
        changed["artifact_evidence"][name]["file"]="link"
        with self.assertRaisesRegex(EvidenceRejected,"Symlink"):
            verify(changed,self.auditors,self.root)

    def test_unknown_signer_and_wrong_signature_fail(self):
        changed=copy.deepcopy(self.manifest)
        changed["auditor_attestation"]["key_id"]="unauthorized"
        with self.assertRaisesRegex(EvidenceRejected,"not uniquely trusted"):
            verify(changed,self.auditors,self.root)
        changed=copy.deepcopy(self.manifest)
        changed["auditor_attestation"]["signature_base64"]=base64.b64encode(b"x"*64).decode()
        with self.assertRaisesRegex(EvidenceRejected,"did NOT sign"):
            verify(changed,self.auditors,self.root)

    def test_every_gate_cannot_reuse_a_single_fake_report(self):
        changed=copy.deepcopy(self.manifest)
        same=next(iter(changed["artifact_evidence"].values()))
        changed["artifact_evidence"]={name:same for name in changed["artifact_evidence"]}
        with self.assertRaisesRegex(EvidenceRejected,"separately inspectable"):
            verify(changed,self.auditors,self.root)

if __name__=="__main__":
    unittest.main()
