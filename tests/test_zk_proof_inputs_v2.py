import tempfile
import unittest
from pathlib import Path
from scripts.patch_zk_proof_inputs_v2 import patch

class ZkProofInputsV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        f = self.root / "wormhole/inputs/src/lib.rs"
        f.parent.mkdir(parents=True)
        f.write_text("pub struct PublicCircuitInputs {\n    pub input_amount: u32,\n}\n")

    def test_adds_real_proof_input_module(self):
        patch(self.root)
        lib = (self.root / "wormhole/inputs/src/lib.rs").read_text()
        module = (self.root / "wormhole/inputs/src/devnira_v2.rs").read_text()
        self.assertIn("pub mod devnira_v2;", lib)
        self.assertIn("ConservationViolation", module)
        self.assertIn("dvn_v2_accepts_exact_eight_decimal_base_units", module)
        self.assertIn("pub input_amount: u32", lib, "V1 remains unchanged until full migration")

    def test_rejects_reapplication(self):
        patch(self.root)
        with self.assertRaisesRegex(ValueError, "already applied"):
            patch(self.root)

    def test_source_drift_rejected(self):
        (self.root / "wormhole/inputs/src/lib.rs").write_text("unknown upstream API")
        with self.assertRaisesRegex(ValueError, "Unexpected upstream"):
            patch(self.root)

if __name__ == "__main__":
    unittest.main()
