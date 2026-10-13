"""Prevent reintroducing an always-failing production gate into development CI."""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/four-component-build.yml"
PRODUCTION_WORKFLOW = ROOT / ".github/workflows/production-build.yml"


class FourComponentCiStatusTests(unittest.TestCase):
    def test_development_job_never_fails_only_because_production_is_incomplete(self):
        source = WORKFLOW.read_text()
        self.assertIn("candidate-summary:", source)
        self.assertIn("test \"$ZK\" = success", source)
        self.assertIn("test \"$RUNTIME\" = success", source)
        self.assertIn("test \"$WINDOWS\" = success", source)
        self.assertIn("test \"$GPU\" = success", source)
        self.assertIn("if python3 scripts/release_evidence_gate.py evidence.json", source)
        self.assertNotIn("  release-gate:", source)
        self.assertIn("NOT RELEASE READY:", source)
        self.assertIn("production-blockers.txt", source)

    def test_separate_production_build_still_rejects_unintegrated_runtime(self):
        source = PRODUCTION_WORKFLOW.read_text()
        self.assertIn("scripts/audit_production_runtime.py upstream", source)
        self.assertIn("Validate independent mainnet genesis", source)

if __name__ == "__main__":
    unittest.main()
