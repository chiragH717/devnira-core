import unittest
from scripts.release_evidence_gate import REQUIRED, audit


class ReleaseEvidenceGateTests(unittest.TestCase):
    def test_empty_is_not_a_release(self):
        failures = audit({})
        self.assertGreaterEqual(len(failures), 20)
        self.assertTrue(any("independent DVN" in f for f in failures))

    def test_partial_development_green_jobs_are_not_a_release(self):
        failures = audit({"network": "quantus-dev", "genesis_hash": "0x" + "1" * 64,
                          "zk_active_proof": {"active_poseidon2_v2": True},
                          "runtime_genesis": {"native_wasm_dvn_runtime": True}})
        self.assertIn("network: independent DVN identity not verified", failures)
        self.assertTrue(any("signed_transfer_roundtrip" in f for f in failures))
        self.assertTrue(any("nvidia_gpu_proof" in f for f in failures))

    def test_complete_evidence_shape(self):
        evidence = {"network": "devnira-independent", "genesis_hash": "0x" + "0" * 64}
        for group, fields in REQUIRED.items():
            evidence[group] = {field: True for field in fields}
        self.assertEqual(audit(evidence), [])
        evidence["windows_wallet"]["secure_key_storage"] = False
        self.assertEqual(len(audit(evidence)), 1)

    def test_raises_on_invalid_shape(self):
        with self.assertRaises(ValueError):
            audit([])


if __name__ == "__main__":
    unittest.main()
