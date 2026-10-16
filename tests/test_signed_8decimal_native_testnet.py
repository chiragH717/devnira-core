"""Signed-native TESTNET branch safety, not proof of a real signed transfer."""
import tempfile
import unittest
from pathlib import Path
from scripts.patch_signed_8decimal_native_testnet import patch, MARKER, FILTER_AFTER
class SignedNativeDevnetSafetyTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        (self.root/"runtime/src/configs").mkdir(parents=True)
        (self.root/"node/src").mkdir(parents=True)
        self.runtime=self.root/"runtime/src/lib.rs"
        self.config=self.root/"runtime/src/configs/mod.rs"
        self.spec=self.root/"node/src/chain_spec.rs"
        self.runtime.write_text(
            "// DEVNIRA ISOLATED EIGHT DECIMAL RUNTIME - NO USER TRANSFERS\n"
            "pub const UNIT: Balance = 100_000_000;\n"
            'spec_name: alloc::borrow::Cow::Borrowed("devnira-8dec-inert-dev-runtime"),\n'
            'impl_name: alloc::borrow::Cow::Borrowed("devnira-8dec-inert-dev-runtime"),\n'
            "frame_system::CheckGenesis<Runtime>,\n"
            "frame_system::CheckNonce<Runtime>,\n"
            "\ttransaction_extensions::WormholeProofRecorderExtension<Runtime>,\n"
            "pallet_transaction_payment::ChargeTransactionPayment<Runtime>,\n")
        self.config.write_text(
            "// DEVNIRA INERT 8-DECIMAL RESEARCH: ALL USER PAYMENTS DISABLED\n"
            'type BaseCallFilter = DvnResearchOnlyCallFilter;\n'
            "matches!(call, RuntimeCall::Timestamp(_) | RuntimeCall::System(_))\n")
        self.spec.write_text(
            'with_id("devnira-8dec-inert-dev")\n'
            'with_protocol_id("devnira-8dec-inert-dev")\n'
            '"DEVNIRA isolated 8-decimal research / NO SEND"\n')
    def test_native_allowlist_only_and_legacy_wormhole_removed(self):
        patch(self.root)
        c=self.config.read_text()
        r=self.runtime.read_text()
        s=self.spec.read_text()
        self.assertIn(FILTER_AFTER,c)
        self.assertNotIn("WormholeProofRecorderExtension<Runtime>",r)
        self.assertNotIn("RuntimeCall::Wormhole",FILTER_AFTER)
        self.assertNotIn("RuntimeCall::Utility",FILTER_AFTER)
        self.assertIn("CheckGenesis<Runtime>",r)
        self.assertIn("CheckNonce<Runtime>",r)
        self.assertIn("ChargeTransactionPayment<Runtime>",r)
        self.assertIn(MARKER,r)
        self.assertEqual(s.count("devnira-8dec-native-dev-test"),2)
        with self.assertRaisesRegex(ValueError,"already installed"):patch(self.root)
    def test_wrong_original_network_filter_or_runtime_rejected_atomically(self):
        for p,old in [
            (self.config,"RuntimeCall::Timestamp(_) | RuntimeCall::System(_)"),
            (self.runtime,"WormholeProofRecorderExtension<Runtime>"),
            (self.spec,"devnira-8dec-inert-dev")
        ]:
            source=p.read_text()
            p.write_text(source.replace(old,"UNEXPECTED_DRIFT"))
            snapshot=tuple(x.read_text() for x in (self.runtime,self.config,self.spec))
            with self.assertRaisesRegex(ValueError,"STOP"):patch(self.root)
            self.assertEqual(snapshot,tuple(x.read_text() for x in (self.runtime,self.config,self.spec)))
            p.write_text(source)
if __name__=="__main__":
    unittest.main()
