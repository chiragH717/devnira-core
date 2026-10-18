"""Only NEW integration contracts. Real binary compile in GitHub CI."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch as mocked
from scripts import compose_stage2_prewallet_devnet as m
from scripts.patch_signed_8decimal_native_testnet import FILTER_AFTER
class CompositeContracts(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        for filename in m.WATCH:
            f=self.root/filename
            f.parent.mkdir(parents=True,exist_ok=True)
            text="\n".join(m.INVARIANTS.get(filename,()))+"\n"
            if filename=="runtime/src/configs/mod.rs":text+="\n"+FILTER_AFTER+"\n"
            f.write_text(text,encoding="utf-8")
    def test_eight_stage_order_and_no_production_claims(self):
        self.assertEqual(len(m.ORDER),8)
        stages=[a for a,b in m.ORDER]
        self.assertLess(stages.index("native_signed_balances_ONLY_no_V1_recorder"),
                        stages.index("default_disabled_V2_header_bridge"))
        digests=m.verify_post_composition(self.root)
        self.assertEqual(set(digests),set(m.WATCH))
        with mocked.object(m,"ORDER",tuple((name,lambda root:None) for name,_ in m.ORDER)):
            report=m.assemble(self.root)
        self.assertEqual(report["stages"],stages)
        self.assertFalse(report["signed_transfer_roundtrip_verified"])
        self.assertFalse(report["two_nodes_finalized_verified"])
        self.assertFalse(report["v2_proof_verifier_activated"])
        self.assertFalse(report["mainnet_approved"])
    def test_legacy_recorder_and_header_activation_rejected(self):
        source=self.root/"runtime/src/lib.rs"
        source.write_text(source.read_text()+"WormholeProofRecorderExtension<Runtime>")
        with self.assertRaisesRegex(ValueError,"legacy 12-decimal"):
            m.verify_post_composition(self.root)
        source.write_text(source.read_text().replace("WormholeProofRecorderExtension<Runtime>",""))
        zk=self.root/"pallets/zk-tree/src/lib.rs"
        zk.write_text(zk.read_text()+"DvnV2HeaderMode::<T>::put(true)")
        with self.assertRaisesRegex(ValueError,"mode activated"):
            m.verify_post_composition(self.root)
    def test_public_custody_broad_filter_and_missing_root_rejected(self):
        w=self.root/"pallets/wormhole/src/lib.rs"
        w.write_text(w.read_text()+"pub fn devnira_v2_record_native_escrow_internal")
        with self.assertRaisesRegex(ValueError,"custody was accidentally made public"):
            m.verify_post_composition(self.root)
        w.write_text(w.read_text().replace("pub fn devnira_v2_record_native_escrow_internal",""))
        cfg=self.root/"runtime/src/configs/mod.rs"
        cfg.write_text(cfg.read_text().replace(FILTER_AFTER,"matches!(call, true)"))
        with self.assertRaisesRegex(ValueError,"native DEV allowlist"):
            m.verify_post_composition(self.root)
        cfg.write_text(cfg.read_text().replace("matches!(call, true)",FILTER_AFTER))
        sys=self.root/"pallets/frame-system/src/lib.rs"
        sys.write_text(sys.read_text().replace("DEVNIRA_V2_HEADER_MODE_DISABLED_UNTIL_SEPARATE_RUNTIME_APPROVAL","DRIFT"))
        with self.assertRaisesRegex(ValueError,"missing integration invariant"):
            m.verify_post_composition(self.root)
if __name__=="__main__":unittest.main()
