import tempfile
import unittest
from pathlib import Path
from scripts.patch_isolated_dvn_8decimal_runtime import patch,RUNTIME_MARKER,FILTER_MARKER

class ResearchOnlyDvnEightDecimalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        files={
            "runtime/src/lib.rs": (
                'spec_name: alloc::borrow::Cow::Borrowed("quantus-runtime"),\n'
                'impl_name: alloc::borrow::Cow::Borrowed("quantus-runtime"),\n'
                'pub const UNIT: Balance = 1_000_000_000_000;\n'
                'pub const MILLI_UNIT: Balance = 1_000_000_000;\n'
                'pub const MICRO_UNIT: Balance = 1_000_000;\n'
                '/// Hard cap on total issuance; mining emissions stop here.\n'
                'pub const MAX_SUPPLY: Balance = 21_000_000 * UNIT;\n'
            ),
            "runtime/src/configs/mod.rs": (
                "pub const SS58Prefix: u8 = 189;\n"
                "#[derive_impl(frame_system::config_preludes::SolochainDefaultConfig)]\n"
                "impl frame_system::Config for Runtime {\n"
                "\ttype Block = Block;\n"
                "}\n"),
            "node/src/command.rs":"DEVNIRA PRE-RELEASE: only --chain dev or --chain devnira-local",
            "Cargo.toml":'qp-wormhole-prover={ version = "=4.3.0" }',
            "pallets/zk-tree/src/tree.rs":"pub const AMOUNT_SCALE_DOWN_FACTOR: u128 = 10_000_000_000;",
            "pallets/wormhole/src/lib.rs":"pub const SCALE_DOWN_FACTOR: u128 = 10_000_000_000;",
            "node/src/chain_spec.rs": (
                'pub fn development_chain_spec() -> Result<ChainSpec, String> {\n'
                '\tproperties.insert("tokenDecimals".into(), json!(12));\n'
                '\tproperties.insert("tokenSymbol".into(), json!("DEV"));\n'
                '\tproperties.insert("ss58Format".into(), json!(189));\n'
                '\tWASM_BINARY.ok_or_else(|| "Quantus DevNet wasm not available".to_string())?;\n'
                '\t.with_name("Quantus DevNet")\n'
                '\t.with_id("dev")\n'
                '\t.with_protocol_id("quantus-devnet")\n'
                '}\n')
        }
        for path,text in files.items():
            p=self.root/path
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(text)
    def test_prototype_source_has_exact_8_decimal_metadata_but_no_spending(self):
        patch(self.root)
        runtime=(self.root/"runtime/src/lib.rs").read_text()
        cfg=(self.root/"runtime/src/configs/mod.rs").read_text()
        dev=(self.root/"node/src/chain_spec.rs").read_text()
        self.assertIn(RUNTIME_MARKER,runtime)
        self.assertIn(FILTER_MARKER,cfg)
        self.assertIn("pub const UNIT: Balance = 100_000_000;",runtime)
        self.assertIn("pub const MAX_SUPPLY: Balance = 100_000_000 * UNIT;",runtime)
        self.assertIn("type BaseCallFilter = DvnResearchOnlyCallFilter",cfg)
        self.assertIn("matches!(call, RuntimeCall::Timestamp(_) | RuntimeCall::System(_))",cfg)
        self.assertIn('json!(8)',dev)
        self.assertIn('json!("DVN")',dev)
        self.assertIn('json!(190)',dev)
        self.assertIn('"devnira-8dec-inert-dev"',dev)
        self.assertIn("SCALE_DOWN_FACTOR", (self.root/"pallets/wormhole/src/lib.rs").read_text())
        with self.assertRaisesRegex(ValueError,"already applied"):
            patch(self.root)

    def test_refuses_foreign_network_selector_before_any_mutation(self):
        (self.root/"node/src/command.rs").write_text("unlocked quantus")
        before=(self.root/"runtime/src/lib.rs").read_text()
        with self.assertRaisesRegex(ValueError,"disable all Quantus"):
            patch(self.root)
        self.assertEqual(before,(self.root/"runtime/src/lib.rs").read_text())

    def test_rejects_missing_v1_proof_regime(self):
        (self.root/"pallets/wormhole/src/lib.rs").write_text("new real V2 proof")
        with self.assertRaisesRegex(ValueError,"withdrawal amount scale changed"):
            patch(self.root)

if __name__=="__main__":
    unittest.main()
