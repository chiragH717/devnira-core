"""Six-stream release evidence tests use synthetic fixture files only."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.release_evidence_gate import REQUIRED
from scripts.six_gate_release_snapshot import CRITICAL_REPORTS, SIX_GATES, requirement_ids, snapshot, markdown
REV = "f" * 40
class SixGateSnapshotTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        (self.root/"config").mkdir()
        genesis=json.loads((Path(__file__).resolve().parents[1]/"config/genesis-proposal.json").read_text())
        (self.root/"config/genesis-proposal.json").write_text(json.dumps(genesis))
        (self.root/"config/trusted-release-auditors.json").write_text(json.dumps({"approved_ed25519_auditors":[]}))
    def test_six_streams_partition_entire_existing_release_schema(self):
        ids=requirement_ids()
        allids={a+"."+f for a,fields in REQUIRED.items() for f in fields}
        self.assertEqual(set(ids),allids)
        self.assertEqual(len(ids),len(allids))
        self.assertEqual(len(SIX_GATES),6)
        critical=[x for entries in CRITICAL_REPORTS.values() for x in entries]
        self.assertEqual(len(critical),13)
        self.assertEqual(len(critical),len(set(critical)))
    def test_green_development_is_not_launch_evidence(self):
        report=snapshot(self.root,REV)
        self.assertFalse(report["signed_release_evidence_admitted"])
        self.assertFalse(report["eligible_for_manual_release_review"])
        self.assertFalse(report["mainnet_deployed"])
        self.assertEqual(report["gate_count"],6)
        self.assertTrue(all(x["status"]=="BLOCKED" for x in report["gates"].values()))
        self.assertIn("Owner-verified public treasury address still absent",report["blocking_conditions"])
        self.assertIn("No independently approved auditor public signing key",report["blocking_conditions"])
        self.assertIn("Real signed release evidence manifest is missing",report["blocking_conditions"])
        self.assertIn("NOT DEPLOYED",markdown(report))
    def test_bad_revision_rejected(self):
        for revision in ("a"*39,"A"*40,"0x"+"a"*40,"foo"):
            with self.subTest(revision=revision),self.assertRaises(ValueError):
                snapshot(self.root,revision)
    def test_forged_all_true_fields_not_an_external_audit(self):
        forged={"network":"devnira-independent","genesis_hash":"0x"+"a"*64,
                "git_revision":REV,"artifact_evidence":{}}
        for group,fields in REQUIRED.items():
            forged[group]={f:True for f in fields}
        (self.root/"config/release-evidence.json").write_text(json.dumps(forged))
        report=snapshot(self.root,REV)
        self.assertFalse(report["signed_release_evidence_admitted"])
        self.assertTrue(any("Signed production evidence rejected" in x for x in report["blocking_conditions"]))
    def test_genesis_economic_drift_blocks(self):
        p=self.root/"config/genesis-proposal.json"
        data=json.loads(p.read_text())
        data["base_units_per_coin"]=1_000_000_000_000
        data["company_treasury"]["instant_units"]=5
        p.write_text(json.dumps(data))
        report=snapshot(self.root,REV)
        self.assertFalse(report["genesis_policy_inputs_complete"])
        self.assertTrue(any("base_units_per_coin" in x for x in report["blocking_conditions"]))
        self.assertTrue(any("3M liquid" in x for x in report["blocking_conditions"]))
    def make_synthetic_reports(self):
        proposal=self.root/"config/genesis-proposal.json"
        value=json.loads(proposal.read_text())
        value["company_treasury"]["public_address"]="TEST_FIXTURE_NOT_A_REAL_ADDRESS"
        value["genesis_timestamp_ms"]=2000000000000
        proposal.write_text(json.dumps(value))
        folder=self.root/"evidence/production"
        folder.mkdir(parents=True)
        reports={}
        for name in (n for group in CRITICAL_REPORTS.values() for n in group):
            b=("SYNTHETIC_NOT_LIVE_"+name).encode()
            path=folder/(name+".txt")
            path.write_bytes(b)
            reports[name]={"file":path.name,"sha256":hashlib.sha256(b).hexdigest()}
        manifest={"git_revision":REV,"critical_acceptance_evidence":reports}
        (self.root/"config/release-evidence.json").write_text(json.dumps(manifest))
        return manifest
    def test_explicit_critical_history_settlement_gpu_reports_required(self):
        manifest=self.make_synthetic_reports()
        # Mocked signature is ONLY an isolated orchestration unit test.
        with patch("scripts.six_gate_release_snapshot.verify",return_value={"signed_manifest_verified":True}):
            report=snapshot(self.root,REV)
            self.assertTrue(report["signed_release_evidence_admitted"])
            self.assertTrue(report["eligible_for_manual_release_review"])
            self.assertFalse(report["mainnet_deployed"])
            manifest["critical_acceptance_evidence"].pop("consensus_header_contains_independent_v2_root")
            (self.root/"config/release-evidence.json").write_text(json.dumps(manifest))
            self.assertFalse(snapshot(self.root,REV)["signed_release_evidence_admitted"])
    def test_revision_mismatch_and_sha_tampering_reject(self):
        manifest=self.make_synthetic_reports()
        with patch("scripts.six_gate_release_snapshot.verify",return_value={"signed_manifest_verified":True}):
            self.assertFalse(snapshot(self.root,"a"*40)["signed_release_evidence_admitted"])
            name=manifest["critical_acceptance_evidence"]["consensus_header_contains_independent_v2_root"]["file"]
            (self.root/"evidence/production"/name).write_bytes(b"TAMPERED")
            report=snapshot(self.root,REV)
            self.assertFalse(report["signed_release_evidence_admitted"])
            self.assertTrue(any("SHA256 evidence mismatch" in x for x in report["blocking_conditions"]))
if __name__=="__main__":
    unittest.main()
