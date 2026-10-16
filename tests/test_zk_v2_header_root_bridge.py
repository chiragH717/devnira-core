import tempfile
import unittest
from pathlib import Path
from scripts.patch_zk_v2_header_root_bridge import patch,MARKER
class HeaderBridgeTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        system=self.root/"pallets/frame-system/src"
        system.mkdir(parents=True)
        self.sy=system/"lib.rs"
        self.sy.write_text("\tpub(super) type ZkTreeRoot<T: Config> = StorageValue<_, T::Hash, ValueQuery>;\n")
        a=self.root/"pallets/zk-tree/src"
        b=self.root/"pallets/wormhole/src"
        a.mkdir(parents=True);b.mkdir(parents=True)
        self.zk=a/"lib.rs"
        self.wh=b/"lib.rs"
        self.ts=b/"tests.rs"
        self.zk.write_text(
            "\t#[pallet::event]\n\t#[pallet::generate_deposit(pub(super) fn deposit_event)]\n"
            "\t\t\tlet root: Hash256 = Root::<T>::get();\n"
            "\t\t\t<frame_system::Pallet<T>>::set_zk_tree_root(root.into());\n")
        self.wh.write_text(
            "// DEVNIRA_V2_CUSTODY_MERKLE_DEPTH16_NON_HEADER\n"
            "        // V2 state snapshot at end of block: NOT chain finality or a header root.\n"
            "        fn on_finalize(n: BlockNumberFor<T>) {\n"
            "            if DvnV2TreeDirty::<T>::take() {\n"
            "                DvnV2TreeHistory::<T>::insert(\n"
            "                    n,(DvnV2TreeRoot::<T>::get(),DvnV2TreeCount::<T>::get()));\n"
            "            }\n"
            "        }\n")
        self.ts.write_text(
            "// DEVNIRA_V2_NATIVE_ESCROW_CUSTODY_NATIVE_FRAME_TESTS\n"
            "    #[test]\n"
            "    fn dvn_v2_deposit_bad_alias_zero_overflow_vault_and_failed_debit_reject(){\n")
    def test_safe_explicit_root_selector(self):
        patch(self.root)
        z=self.zk.read_text()
        w=self.wh.read_text()
        t=self.ts.read_text()
        self.assertIn(MARKER,self.sy.read_text())
        for needle in ["frame_system::DvnV2HeaderMode::<T>::get()","frame_system::DvnV2HeaderRootCandidate::<T>::take()",
                       "LeafCount::<T>::get()==0"]:
            self.assertIn(needle,z)
        self.assertIn("frame_system::DvnV2HeaderRootCandidate::<T>::put(root)",w)
        self.assertIn("DvnV2TreeHistory::<T>::insert(",w)
        self.assertIn("dvn_v2_deposit_header_bridge_optin_sets_actual_frame_system_root",t)
        self.assertIn("dvn_v2_deposit_header_bridge_remains_disabled_by_default",t)
        with self.assertRaisesRegex(ValueError,"already present"):patch(self.root)
    def test_unexpected_upstream_data_never_partially_patches(self):
        for f,key in [(self.zk,"let root: Hash256 = Root::<T>::get();"),
                      (self.wh,"DvnV2TreeDirty::<T>::take()"),
                      (self.ts,"DEVNIRA_V2_NATIVE_ESCROW_CUSTODY_NATIVE_FRAME_TESTS")]:
            orig=f.read_text()
            f.write_text(orig.replace(key,"DRIFT"))
            snap=tuple(p.read_text() for p in (self.sy,self.zk,self.wh,self.ts))
            with self.assertRaisesRegex(ValueError,"STOP"):patch(self.root)
            self.assertEqual(snap,tuple(p.read_text() for p in (self.sy,self.zk,self.wh,self.ts)))
            f.write_text(orig)
if __name__=="__main__":
    unittest.main()
