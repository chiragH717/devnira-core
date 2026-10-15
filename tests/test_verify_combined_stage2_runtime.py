import tempfile
import unittest
from pathlib import Path
from scripts.verify_combined_stage2_runtime import verify,CONDITIONS,FILES

class CombinedNativeWasmCandidateGuards(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        grouped={name:[] for name in FILES}
        for component,(where,needle) in CONDITIONS.items():
            grouped[where].append(needle)
        for name,path in FILES.items():
            f=self.root/path
            f.parent.mkdir(parents=True,exist_ok=True)
            f.write_text("\n".join(grouped[name])+"\n")
        cfg=self.root/FILES["configs"]
        cfg.write_text(cfg.read_text()+
            "impl frame_support::traits::Contains<RuntimeCall> for DvnResearchOnlyCallFilter {}\n")
        source=self.root/FILES["wormhole"]
        source.write_text(source.read_text()+
            "pub(crate) fn devnira_v2_leaf_chain_preflight(x:u8){}\n")
    def test_exact_same_source_can_prove_all_development_guards(self):
        result=verify(self.root)
        self.assertTrue(result["all_source_safety_checks_passed"])
        for key in ("user_transactions_enabled","active_v2_proof_verifier",
                    "real_genesis_built","independent_mainnet_ready"):
            self.assertFalse(result[key])

    def test_every_required_gate_rejects_missing_component(self):
        for name,(where,needle) in CONDITIONS.items():
            with self.subTest(name=name):
                file=self.root/FILES[where]
                previous=file.read_text()
                file.write_text(previous.replace(needle,"REMOVED",1))
                with self.assertRaisesRegex(ValueError,"NOT A VALID"):
                    verify(self.root)
                file.write_text(previous)

    def test_unverified_v2_dispatch_and_mainnet_promotion_rejected(self):
        file=self.root/FILES["wormhole"]
        old=file.read_text()
        file.write_text(old.replace("pub(crate) fn devnira_v2_leaf_chain_preflight",
                                    "pub fn devnira_v2_leaf_chain_preflight"))
        with self.assertRaisesRegex(ValueError,"exposed"):
            verify(self.root)
        file.write_text(old)
        f=self.root/FILES["chain_spec"]
        f.write_text(f.read_text()+'\nwith_id("devnira-mainnet-v1")')
        with self.assertRaisesRegex(ValueError,"exposed"):
            verify(self.root)

    def test_missing_rust_module_rejected(self):
        (self.root/FILES["vesting"]).unlink()
        with self.assertRaisesRegex(ValueError,"Missing required"):
            verify(self.root)

if __name__=="__main__":
    unittest.main()
