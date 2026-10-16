#!/usr/bin/env python3
"""Stage consensus-header V2 root selector at exact pinned FRAME source.

DEVELOPMENT ONLY: mode is disabled by default, no public V2 activation or Send.
Must be applied after native tree/custody/leaf/depth16 patches.
"""
import argparse
from pathlib import Path

MARKER="DEVNIRA_V2_HEADER_MODE_DISABLED_UNTIL_SEPARATE_RUNTIME_APPROVAL"
HEADER_SOURCE=r'''
    // DEVNIRA_V2_HEADER_MODE_DISABLED_UNTIL_SEPARATE_RUNTIME_APPROVAL
    // Runtime/genesis must consciously opt in. NO dispatchable toggle.
    #[pallet::storage]
    pub type DvnV2HeaderMode<T:Config>=StorageValue<_,bool,ValueQuery>;
    // At most one per-block root provided by internal custody Merkle state.
    // This is NOT proof of consensus approval or a historical block hash.
    #[pallet::storage]
    pub type DvnV2HeaderRootCandidate<T:Config>=StorageValue<_,[u8;32],OptionQuery>;

'''
PUBLISH_OLD='''\t\t\tlet root: Hash256 = Root::<T>::get();
\t\t\t<frame_system::Pallet<T>>::set_zk_tree_root(root.into());'''
PUBLISH_NEW='''            // DEVNIRA V2 header bridge (opt-in only): selection happens
            // exactly once in the LAST ZkTree on_finalize hook. A V2 header
            // cannot silently combine 12-decimal V1 leaves with V2 custody.
            // Unconfigured mode preserves original upstream V1 behavior.
            let root:Hash256=if frame_system::DvnV2HeaderMode::<T>::get(){
                assert!(LeafCount::<T>::get()==0
                    && UnprocessedLeaves::<T>::get()==0,
                    "STOP: legacy V1 leaves exist in V2-only header mode");
                frame_system::DvnV2HeaderRootCandidate::<T>::take().expect(
                    "STOP: missing per-block V2 custody header root")
            }else{
                assert!(frame_system::DvnV2HeaderRootCandidate::<T>::get().is_none(),
                    "STOP: V2 root submitted while consensus mode disabled");
                Root::<T>::get()
            };
            <frame_system::Pallet<T>>::set_zk_tree_root(root.into());'''
WORMHOLE_OLD='''        // V2 state snapshot at end of block: NOT chain finality or a header root.
        fn on_finalize(n: BlockNumberFor<T>) {
            if DvnV2TreeDirty::<T>::take() {
                DvnV2TreeHistory::<T>::insert(
                    n,(DvnV2TreeRoot::<T>::get(),DvnV2TreeCount::<T>::get()));
            }
        }
'''
WORMHOLE_NEW='''        // In explicit opt-in mode a distinct FRAME header-root candidate
        // must be produced EVERY block, even if no deposit happened. The
        // ZkTree pallet (after Wormhole) consumes it into system header.
        // This is NOT sufficient evidence of finalized/network consensus.
        fn on_finalize(n: BlockNumberFor<T>) {
            if frame_system::DvnV2HeaderMode::<T>::get() {
                let root=DvnV2TreeRoot::<T>::get();
                DvnV2TreeHistory::<T>::insert(
                    n,(root,DvnV2TreeCount::<T>::get()));
                frame_system::DvnV2HeaderRootCandidate::<T>::put(root);
                DvnV2TreeDirty::<T>::kill();
            } else if DvnV2TreeDirty::<T>::take() {
                DvnV2TreeHistory::<T>::insert(
                    n,(DvnV2TreeRoot::<T>::get(),DvnV2TreeCount::<T>::get()));
            }
        }
'''
TESTS=r'''
    #[test]
    fn dvn_v2_deposit_header_bridge_optin_sets_actual_frame_system_root() {
        use frame_support::traits::Hooks;
        let sender=account_id(1);
        let vault=Wormhole::devnira_v2_custody_escrow_account();
        new_test_ext_with_endowments(vec![
            (sender.clone(),1000*UNIT),(vault.clone(),10*UNIT)
        ]).execute_with(||{
            // Deliberate opt-in test, NOT default upstream chain behavior.
            frame_system::DvnV2HeaderMode::<Test>::put(true);
            System::set_block_number(2);
            assert_eq!(Wormhole::devnira_v2_record_native_escrow_internal(
                &sender,&owner(),1),Ok(0));
            let native_root=DvnV2TreeRoot::<Test>::get();
            assert_ne!(native_root,[0u8;32]);
            assert_eq!(ZkTree::leaf_count(),0);
            // Real hook order in runtime: Wormhole BEFORE ZkTree.
            Wormhole::on_finalize(2);
            assert_eq!(frame_system::DvnV2HeaderRootCandidate::<Test>::get(),
                Some(native_root));
            ZkTree::on_finalize(2);
            let exposed=System::zk_tree_root();
            assert_eq!(exposed.as_ref(),native_root.as_ref());
            assert!(frame_system::DvnV2HeaderRootCandidate::<Test>::get().is_none());
            assert_eq!(DvnV2TreeHistory::<Test>::get(2),Some((native_root,1)));
            System::set_block_number(3);
            Wormhole::on_finalize(3);
            ZkTree::on_finalize(3);
            assert_eq!(System::zk_tree_root().as_ref(),native_root.as_ref());
            assert_eq!(DvnV2TreeHistory::<Test>::get(3),Some((native_root,1)));
        });
    }
    #[test]
    fn dvn_v2_deposit_header_bridge_remains_disabled_by_default(){
        use frame_support::traits::Hooks;
        new_test_ext().execute_with(||{
            assert!(!frame_system::DvnV2HeaderMode::<Test>::get());
            System::set_block_number(2);
            Wormhole::on_finalize(2);
            assert!(frame_system::DvnV2HeaderRootCandidate::<Test>::get().is_none());
            ZkTree::on_finalize(2);
            let legacy=pallet_zk_tree::Root::<Test>::get();
            assert_eq!(System::zk_tree_root().as_ref(),legacy.as_ref());
        });
    }
    #[test]
    #[should_panic(expected="STOP: legacy V1 leaves exist in V2-only header mode")]
    fn dvn_v2_deposit_header_bridge_rejects_legacy_v1_merkle_mix(){
        use frame_support::traits::Hooks;
        new_test_ext().execute_with(||{
            frame_system::DvnV2HeaderMode::<Test>::put(true);
            System::set_block_number(2);
            ZkTree::insert_leaf(owner(),0,0u32,UNIT);
            Wormhole::on_finalize(2);
            ZkTree::on_finalize(2);
        });
    }
'''
def replace_once(data,old,new,label):
    found=data.count(old)
    if found!=1: raise ValueError("STOP: pinned FRAME source mismatch "+label+": "+str(found))
    return data.replace(old,new,1)
def patch(root:Path)->None:
    system=root/"pallets/frame-system/src/lib.rs"
    z=root/"pallets/zk-tree/src/lib.rs"
    w=root/"pallets/wormhole/src/lib.rs"
    t=root/"pallets/wormhole/src/tests.rs"
    old_s=system.read_text(encoding="utf-8")
    old_z=z.read_text(encoding="utf-8")
    old_w=w.read_text(encoding="utf-8")
    old_t=t.read_text(encoding="utf-8")
    if MARKER in old_s: raise ValueError("STOP: V2 header selector already present")
    if "DEVNIRA_V2_CUSTODY_MERKLE_DEPTH16_NON_HEADER" not in old_w:
        raise ValueError("STOP: independent V2 custody tree missing")
    if "DvnV2TreeHistory::<T>::insert(" not in old_w:
        raise ValueError("STOP: previous V2 block-end snapshot missing")
    if "DEVNIRA_V2_NATIVE_ESCROW_CUSTODY_NATIVE_FRAME_TESTS" not in old_t:
        raise ValueError("STOP: original native custody test suite missing")
    new_s=replace_once(old_s,
        "\tpub(super) type ZkTreeRoot<T: Config> = StorageValue<_, T::Hash, ValueQuery>;\n",
        "\tpub(super) type ZkTreeRoot<T: Config> = StorageValue<_, T::Hash, ValueQuery>;\n"+HEADER_SOURCE,
        "FRAME shared V2 header storage")
    new_z=old_z
    new_z=replace_once(new_z,PUBLISH_OLD,PUBLISH_NEW,"single final root publication")
    new_w=replace_once(old_w,WORMHOLE_OLD,WORMHOLE_NEW,"Wormhole -> ZkTree hook handoff")
    new_t=replace_once(old_t,
        "    #[test]\n    fn dvn_v2_deposit_bad_alias_zero_overflow_vault_and_failed_debit_reject(){",
        TESTS+"    #[test]\n    fn dvn_v2_deposit_bad_alias_zero_overflow_vault_and_failed_debit_reject(){",
        "native FRAME header tests")
    system.write_text(new_s,encoding="utf-8")
    z.write_text(new_z,encoding="utf-8")
    w.write_text(new_w,encoding="utf-8")
    t.write_text(new_t,encoding="utf-8")
    print("V2 opt-in header binding staged. DEFAULT DISABLED; NOT independent finalized network history or active settlement.")
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("pinned_frame_root",type=Path)
    patch(p.parse_args().pinned_frame_root)
