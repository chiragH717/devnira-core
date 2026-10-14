import tempfile
import unittest
from pathlib import Path

from scripts.guard_dvn_network_identity import patch, MARKER

CLI='''impl Test {
	fn load_spec(&self, id: &str) -> Result<Box<dyn sc_service::ChainSpec>, String> {
		Ok(match id {
			"dev" => Box::new(chain_spec::development_chain_spec()?) as Box<dyn sc_service::ChainSpec>,
			"heisenberg_live_spec" => Box::new(chain_spec::heisenberg_chain_spec()?) as Box<dyn sc_service::ChainSpec>,
			"heisenberg" => Box::new(chain_spec::ChainSpec::from_json_bytes(include_bytes!("chain-specs/heisenberg.json"))?) as Box<dyn sc_service::ChainSpec>,
			"planck_live_spec" => Box::new(chain_spec::planck_chain_spec()?) as Box<dyn sc_service::ChainSpec>,
			"planck" => Box::new(chain_spec::ChainSpec::from_json_bytes(include_bytes!("chain-specs/planck.json"))?) as Box<dyn sc_service::ChainSpec>,
			"mainnet_live_spec" => Box::new(chain_spec::mainnet_chain_spec()?) as Box<dyn sc_service::ChainSpec>,
			"mainnet" => Box::new(chain_spec::ChainSpec::from_json_bytes(include_bytes!("chain-specs/mainnet.json"))?) as Box<dyn sc_service::ChainSpec>,
			path => Box::new(chain_spec::ChainSpec::from_json_file(std::path::PathBuf::from(path))?) as Box<dyn sc_service::ChainSpec>,
		})
	}
}
'''

class ForeignChainGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.path=self.root/"node/src/command.rs"
        self.path.parent.mkdir(parents=True)
        self.path.write_text(CLI)
    def test_removes_live_quantus_default_and_file_import(self):
        patch(self.root)
        s=self.path.read_text()
        self.assertIn(MARKER,s)
        self.assertIn('"dev" | "devnira-local"',s)
        self.assertIn("No independent DVN mainnet genesis exists yet",s)
        self.assertNotIn("ChainSpec::from_json_file",s)
        for term in ('"mainnet"','"mainnet_live_spec"','"planck"','"planck_live_spec"',
                     '"heisenberg"','"heisenberg_live_spec"'):
            self.assertNotIn(term,s)
        self.assertEqual(s.count('fn load_spec(&self'),1)
    def test_double_application_fails_closed(self):
        patch(self.root)
        with self.assertRaisesRegex(ValueError,"already applied"):
            patch(self.root)
    def test_foreign_selector_drift_does_not_write_partial_patch(self):
        altered=CLI.replace('"mainnet_live_spec"','"changed_live_spec"')
        self.path.write_text(altered)
        with self.assertRaisesRegex(ValueError,"upstream network selector changed"):
            patch(self.root)
        self.assertEqual(self.path.read_text(),altered)
    def test_missing_file_refuses_to_change(self):
        self.path.unlink()
        with self.assertRaises(FileNotFoundError):
            patch(self.root)

if __name__=="__main__":
    unittest.main()
