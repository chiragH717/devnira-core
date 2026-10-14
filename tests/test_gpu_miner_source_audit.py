import tempfile
import unittest
from pathlib import Path
from scripts.audit_gpu_miner_source import REQUIRED, audit

class GpuMinerCandidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        for file,terms in REQUIRED.items():
            p=self.root/file
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text("\n".join(terms)+"\n")

    def test_cuda_vulkan_and_poseidon_source_evidence_is_not_mining_proof(self):
        evidence=audit(self.root)
        self.assertTrue(evidence["source_audit_passed"])
        self.assertIn("nvidia_cuda",evidence["engines"])
        self.assertIn("amd_vulkan_wgpu",evidence["engines"])
        self.assertFalse(evidence["real_gpu_pow_proven"])
        self.assertFalse(evidence["two_node_dvn_network_proven"])
        self.assertFalse(evidence["protocol_integration_test_passed"])

    def test_missing_cuda_or_amd_or_pow_source_is_hard_failure(self):
        for path in REQUIRED:
            p=self.root/path
            original=p.read_text()
            p.write_text("unreviewed-miner-source-change")
            with self.assertRaisesRegex(ValueError,"source drift"):
                audit(self.root)
            p.write_text(original)

    def test_unknown_source_revisions_do_not_pass_with_empty_files(self):
        for path in REQUIRED:
            (self.root/path).write_text("")
        with self.assertRaisesRegex(ValueError,"STOP"):
            audit(self.root)

if __name__=="__main__":
    unittest.main()
