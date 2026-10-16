#!/usr/bin/env python3
"""Append exact custody receipts to a distinct depth-16 4-ary Poseidon V2 tree.

DEVELOPMENT ONLY. Root snapshots are block-end state, NOT consensus header
history/finality. No dispatchable deposit, active V2 verifier or SEND.
"""
import argparse
from pathlib import Path

MARKER="DEVNIRA_V2_CUSTODY_MERKLE_DEPTH16_NON_HEADER"
HISTORY_MARKER="DEVNIRA_V2_CUSTODY_BLOCK_END_SNAPSHOTS_NOT_FINALITY"
STORAGE=r'''
    // DEVNIRA_V2_CUSTODY_MERKLE_DEPTH16_NON_HEADER
    // This V2 tree is separate from legacy V1 ZkTree Nodes/Root/Header.
    // Only internal escrow writes. Finalized header integration is NOT enabled.
    #[pallet::storage]
    pub type DvnV2TreeCount<T:Config>=StorageValue<_,u64,ValueQuery>;
    #[pallet::storage]
    pub type DvnV2TreeRoot<T:Config>=StorageValue<_,[u8;32],ValueQuery>;
    #[pallet::storage]
    pub type DvnV2TreeNodes<T:Config>=
        StorageMap<_,Blake2_128Concat,(u8,u64),[u8;32],OptionQuery>;
    #[pallet::storage]
    pub type DvnV2TreeDirty<T:Config>=StorageValue<_,bool,ValueQuery>;
    // DEVNIRA_V2_CUSTODY_BLOCK_END_SNAPSHOTS_NOT_FINALITY
    // These are local block-end state snapshots ONLY, never validated headers.
    #[pallet::storage]
    pub type DvnV2TreeHistory<T:Config>=
        StorageMap<_,Twox64Concat,BlockNumberFor<T>,([u8;32],u64),OptionQuery>;

'''
BODY=r'''
        /// Append one already custody-backed immutable Poseidon leaf.
        /// 4-ary depth16 = 4^16 capacity. Consistent with fixed-depth16 circuit
        /// structure, but NOT proof-system/header/domain compatibility approval.
        fn devnira_v2_append_merkle_internal(
            index:u64,leaf:[u8;32]
        )->Result<(),sp_runtime::DispatchError>{
            const DEPTH:u8=16;
            const MAX_LEAVES:u64=1u64<<32;
            ensure!(index==DvnV2TreeCount::<T>::get() && index<MAX_LEAVES,
                Error::<T>::InvalidProofPublicInputs);
            ensure!(DvnV2EscrowCommitment::<T>::get(index)==Some(leaf),
                Error::<T>::InvalidProofPublicInputs);
            let mut cursor=index;
            let mut current=leaf;
            for level in 0..DEPTH{
                let base=cursor-(cursor%4);
                let mut children=[[0u8;32];4];
                for slot in 0..4u64{
                    let at=base+slot;
                    children[slot as usize]=if at==cursor{
                        current
                    }else if level==0{
                        DvnV2EscrowCommitment::<T>::get(at).unwrap_or([0u8;32])
                    }else{
                        DvnV2TreeNodes::<T>::get((level,at)).unwrap_or([0u8;32])
                    };
                }
                current=pallet_zk_tree::tree::hash_node(&children);
                cursor/=4;
                DvnV2TreeNodes::<T>::insert((level+1,cursor),current);
            }
            DvnV2TreeRoot::<T>::put(current);
            DvnV2TreeCount::<T>::put(index+1);
            DvnV2TreeDirty::<T>::put(true);
            Ok(())
        }

        /// Current-root-only sibling proof for an immutable receipt. Because
        /// historical node states are NOT retained, do not use for old roots.
        pub(crate) fn devnira_v2_current_receipt_witness_internal(
            index:u64
        )->Result<Vec<[[u8;32];3]>,Error<T>>{
            ensure!(index<DvnV2TreeCount::<T>::get(),
                Error::<T>::InvalidProofPublicInputs);
            ensure!(DvnV2EscrowCommitment::<T>::contains_key(index),
                Error::<T>::InvalidProofPublicInputs);
            let mut proof=Vec::with_capacity(16);
            let mut cursor=index;
            for level in 0..16u8{
                let base=cursor-(cursor%4);
                let mut siblings=[[0u8;32];3];
                let mut n=0usize;
                for slot in 0..4u64{
                    let at=base+slot;
                    if at==cursor{continue;}
                    siblings[n]=if level==0{
                        DvnV2EscrowCommitment::<T>::get(at).unwrap_or([0u8;32])
                    }else{
                        DvnV2TreeNodes::<T>::get((level,at)).unwrap_or([0u8;32])
                    };
                    n+=1;
                }
                proof.push(siblings);
                cursor/=4;
            }
            Ok(proof)
        }

'''
TEST=r'''
    #[test]
    fn dvn_v2_deposit_fixed_depth16_merkle_root_independent_of_v1(){
        use frame_support::traits::Hooks;
        let sender=account_id(1);
        let vault=Wormhole::devnira_v2_custody_escrow_account();
        new_test_ext_with_endowments(vec![
            (sender.clone(),1000*UNIT),(vault.clone(),10*UNIT)
        ]).execute_with(||{
            System::set_block_number(2);
            let initial_issuance=Balances::total_issuance();
            assert_eq!(DvnV2TreeCount::<Test>::get(),0);
            assert_eq!(DvnV2TreeRoot::<Test>::get(),[0u8;32]);
            let a=owner();
            assert_eq!(Wormhole::devnira_v2_record_native_escrow_internal(
                &sender,&a,1),Ok(0));
            let mut independent=DvnV2EscrowCommitment::<Test>::get(0).unwrap();
            for _ in 0..16{
                independent=pallet_zk_tree::tree::hash_node(
                    &[independent,[0u8;32],[0u8;32],[0u8;32]]);
            }
            assert_eq!(DvnV2TreeCount::<Test>::get(),1);
            assert_eq!(DvnV2TreeRoot::<Test>::get(),independent);
            assert_eq!(DvnV2TreeNodes::<Test>::get((16,0)),Some(independent));
            assert_eq!(ZkTree::leaf_count(),0);
            assert_eq!(Balances::total_issuance(),initial_issuance);
            assert_eq!(DvnV2TreeHistory::<Test>::get(2),None);
            Wormhole::on_finalize(2);
            assert_eq!(DvnV2TreeHistory::<Test>::get(2),Some((independent,1)));
            Wormhole::on_finalize(3);
            assert_eq!(DvnV2TreeHistory::<Test>::get(3),None);
            let previous=independent;
            System::set_block_number(4);
            assert_eq!(Wormhole::devnira_v2_record_native_escrow_internal(
                &sender,&a,2),Ok(1));
            assert_ne!(DvnV2TreeRoot::<Test>::get(),previous);
            Wormhole::on_finalize(4);
            assert_eq!(DvnV2TreeHistory::<Test>::get(4),
                Some((DvnV2TreeRoot::<Test>::get(),2)));
            assert_eq!(DvnV2TreeHistory::<Test>::get(2),Some((previous,1)));
        });
    }
    #[test]
    fn dvn_v2_deposit_current_witness_16_levels_and_tamper_detection(){
        let sender=account_id(1);
        let vault=Wormhole::devnira_v2_custody_escrow_account();
        new_test_ext_with_endowments(vec![
            (sender.clone(),1000*UNIT),(vault.clone(),10*UNIT)
        ]).execute_with(||{
            let another=AccountId32::new([4u8;32]);
            for (to,amount) in [(owner(),1),(owner(),2),(another,3)]{
                assert!(Wormhole::devnira_v2_record_native_escrow_internal(
                    &sender,&to,amount).is_ok());
            }
            let root=DvnV2TreeRoot::<Test>::get();
            assert_eq!(DvnV2TreeCount::<Test>::get(),3);
            for i in 0..3u64{
                let mut current=DvnV2EscrowCommitment::<Test>::get(i).unwrap();
                let proof=Wormhole::devnira_v2_current_receipt_witness_internal(i).unwrap();
                assert_eq!(proof.len(),16);
                for siblings in &proof{
                    current=pallet_zk_tree::tree::hash_node(
                        &[current,siblings[0],siblings[1],siblings[2]]);
                }
                assert_eq!(current,root);
            }
            let mut forged=Wormhole::devnira_v2_current_receipt_witness_internal(0).unwrap();
            forged[0][0][0]^=1;
            let mut current=DvnV2EscrowCommitment::<Test>::get(0).unwrap();
            for sibs in &forged{
                current=pallet_zk_tree::tree::hash_node(
                    &[current,sibs[0],sibs[1],sibs[2]]);
            }
            assert_ne!(current,root,"tampered sibling cannot authenticate root");
            assert!(Wormhole::devnira_v2_current_receipt_witness_internal(3).is_err());
        });
    }
    #[test]
    fn dvn_v2_deposit_failure_cannot_advance_tree_or_snapshot(){
        use frame_support::traits::Hooks;
        let sender=account_id(1);
        let vault=Wormhole::devnira_v2_custody_escrow_account();
        new_test_ext_with_endowments(vec![
            (sender.clone(),1000*UNIT),(vault.clone(),10*UNIT)
        ]).execute_with(||{
            System::set_block_number(2);
            assert!(Wormhole::devnira_v2_record_native_escrow_internal(
                &account_id(99399),&owner(),UNIT).is_err());
            assert_eq!(DvnV2TreeCount::<Test>::get(),0);
            assert_eq!(DvnV2TreeRoot::<Test>::get(),[0u8;32]);
            assert!(!DvnV2TreeDirty::<Test>::get());
            assert!(DvnV2EscrowCommitment::<Test>::get(0).is_none());
            Wormhole::on_finalize(2);
            assert!(DvnV2TreeHistory::<Test>::get(2).is_none());
            // Corrupted count is rejected BEFORE any balance movement.
            DvnV2TreeCount::<Test>::put(1);
            let initial=Balances::balance(&sender);
            assert!(Wormhole::devnira_v2_record_native_escrow_internal(
                &sender,&owner(),1).is_err());
            assert_eq!(Balances::balance(&sender),initial);
            assert_eq!(DvnV2TreeCount::<Test>::get(),1);
            assert_eq!(DvnV2EscrowNextReceipt::<Test>::get(),0);
        });
    }
'''
def once(text,old,new,label):
    if text.count(old)!=1:
        raise ValueError("STOP: upstream source composition differs: "+label)
    return text.replace(old,new,1)

def patch(root:Path):
    lib=root/"pallets/wormhole/src/lib.rs"
    tests=root/"pallets/wormhole/src/tests.rs"
    old=lib.read_text(encoding="utf-8")
    orig_tests=tests.read_text(encoding="utf-8")
    if MARKER in old or HISTORY_MARKER in old:
        raise ValueError("STOP: V2 Merkle tree already installed")
    for required in ("DEVNIRA_V2_CUSTODY_COMMITMENTS_STORAGE_NO_FINALIZED_ROOT",
                     "DEVNIRA_V2_NATIVE_ESCROW_BACKING_INTERNAL_NO_DISPATCH",
                     "DvnV2EscrowCommitment::<T>::insert(id,commitment)",
                     "fn on_initialize(n: BlockNumberFor<T>) -> Weight {"):
        if required not in old:
            raise ValueError("STOP: missing pinned upstream custody prerequisite: "+required)
    if "DEVNIRA_V2_NATIVE_ESCROW_CUSTODY_NATIVE_FRAME_TESTS" not in orig_tests:
        raise ValueError("STOP: native FRAME tests missing")
    if "DvnV2EscrowReceipt" not in orig_tests:
        raise ValueError("STOP: custody tests changed")
    out=once(old,
        "    pub type DvnV2EscrowCommitment<T:Config>=\n        StorageMap<_,Twox64Concat,u64,[u8;32],OptionQuery>;\n",
        "    pub type DvnV2EscrowCommitment<T:Config>=\n        StorageMap<_,Twox64Concat,u64,[u8;32],OptionQuery>;\n"+STORAGE,
        "separate tree storage")
    out=once(out,
        "        /// Which verify path settled the bundle.", 
        "        /// Which verify path settled the bundle.",
        "explicit anchor validation") if False else out
    out=once(out,
        "        /// DEVNIRA_V2_NATIVE_ESCROW_BACKING_INTERNAL_NO_DISPATCH",
        BODY+"        /// DEVNIRA_V2_NATIVE_ESCROW_BACKING_INTERNAL_NO_DISPATCH",
        "internal tree methods")
    out=once(out,
        "                    DvnV2EscrowCommitment::<T>::insert(id,commitment);",
        "                    DvnV2EscrowCommitment::<T>::insert(id,commitment);\n"
        "                    Self::devnira_v2_append_merkle_internal(id,commitment)?;",
        "receipt-to-tree atomic append")
    out=once(out,
        "\t\tfn on_initialize(n: BlockNumberFor<T>) -> Weight {",
        """        // V2 state snapshot at end of block: NOT chain finality or a header root.
        fn on_finalize(n: BlockNumberFor<T>) {
            if DvnV2TreeDirty::<T>::take() {
                DvnV2TreeHistory::<T>::insert(
                    n,(DvnV2TreeRoot::<T>::get(),DvnV2TreeCount::<T>::get()));
            }
        }

\t\tfn on_initialize(n: BlockNumberFor<T>) -> Weight {""",
        "block-end non-final root state")
    new_tests=once(orig_tests,
        "        DvnV2EscrowRecipientCount,DvnV2EscrowReceipt,DvnV2EscrowCommitment};",
        "        DvnV2EscrowRecipientCount,DvnV2EscrowReceipt,DvnV2EscrowCommitment,\n"
        "        DvnV2TreeCount,DvnV2TreeRoot,DvnV2TreeNodes,DvnV2TreeDirty,DvnV2TreeHistory};",
        "new tests storage imports")
    new_tests=once(new_tests,
        "    #[test]\n    fn dvn_v2_deposit_bad_alias_zero_overflow_vault_and_failed_debit_reject(){",
        TEST+"    #[test]\n    fn dvn_v2_deposit_bad_alias_zero_overflow_vault_and_failed_debit_reject(){",
        "real FRAME Merkle tests")
    lib.write_text(out,encoding="utf-8")
    tests.write_text(new_tests,encoding="utf-8")
    print("Independent native custody V2 depth16 Merkle tree + current witness + block-end snapshots staged. NO HEADER FINALITY/SEND.")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("pinned_frame_root",type=Path)
    patch(p.parse_args().pinned_frame_root)
