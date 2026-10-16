#!/usr/bin/env python3
"""Bind every INTERNAL V2 custody receipt to exact native Poseidon leaf hash.

Runs after patch_zk_tree_native_v2.py and patch_zk_v2_native_custody_ledger.py.
This creates immutable per-receipt leaf commitments, NOT a Merkle root/header,
not an actual user-accessible deposit, and NOT a withdrawal authorization.
"""
from pathlib import Path
import argparse

TREE_MARKER="// DEVNIRA V2 CUSTODY RECEIPT POSEIDON LEAF COMPONENTS (NO ROOT)"
LEDGER_MARKER="// DEVNIRA_V2_CUSTODY_COMMITMENTS_STORAGE_NO_FINALIZED_ROOT"

COMPONENT_FN=r'''
// DEVNIRA V2 CUSTODY RECEIPT POSEIDON LEAF COMPONENTS (NO ROOT)
/// Exact native 8-decimal V2 commitment from custody receipt components.
/// Matches hash_leaf_native_v2 for canonical account, transfer_count and native
/// asset_id 0. A commitment alone is NOT an authenticated history/merkle root.
pub fn dvn_native_v2_commitment_from_receipt(
    account_bytes:[u8;32], transfer_count:u64, amount_base_units:u128
)->Result<Hash256,&'static str>{
    use qp_poseidon_core::serialization::u64_to_felts;
    if amount_base_units == 0 || amount_base_units > DVN_NATIVE_MAX_BASE_UNITS_V2{
        return Err("DVN V2 receipt amount invalid");
    }
    if !account_bytes.chunks_exact(8).all(|chunk|{
        let limb:[u8;8]=chunk.try_into().expect("exact 8 bytes");
        u64::from_le_bytes(limb) < GOLDILOCKS_P
    }){
        return Err("DVN V2 receipt account must be canonical");
    }
    let mut felts=Vec::with_capacity(8);
    felts.extend(bytes_to_felts_compact_lossy(&account_bytes));
    felts.extend(u64_to_felts(transfer_count));
    // Asset ID=0 reserved for native DVN. Never hash a synthetic asset credit.
    felts.extend(bytes_to_felts_compact_lossy(&0u64.to_le_bytes()));
    felts.extend(bytes_to_felts_compact_lossy(&(amount_base_units as u64).to_le_bytes()));
    debug_assert_eq!(felts.len(),8);
    Ok(qp_poseidon_core::hash_to_bytes(&felts))
}

'''
LEDGER_STORAGE=r'''
    // DEVNIRA_V2_CUSTODY_COMMITMENTS_STORAGE_NO_FINALIZED_ROOT
    #[pallet::storage]
    pub type DvnV2EscrowCommitment<T:Config>=
        StorageMap<_,Twox64Concat,u64,[u8;32],OptionQuery>;

'''
RUST_TEST=r'''
    #[test]
    fn dvn_v2_deposit_receipt_commitments_match_exact_poseidon_native_tree(){
        let sender=account_id(1);
        let vault=Wormhole::devnira_v2_custody_escrow_account();
        new_test_ext_with_endowments(vec![
            (sender.clone(),1000*UNIT),(vault.clone(),10*UNIT)
        ]).execute_with(||{
            let count=Balances::total_issuance();
            let a=owner();
            let b=AccountId32::new([4u8;32]);
            assert_eq!(Wormhole::devnira_v2_record_native_escrow_internal(
                &sender,&a,1),Ok(0));
            assert_eq!(Wormhole::devnira_v2_record_native_escrow_internal(
                &sender,&a,2),Ok(1));
            assert_eq!(Wormhole::devnira_v2_record_native_escrow_internal(
                &sender,&b,3),Ok(2));
            for (id,who,seq,value) in [
                (0u64,a.clone(),0u64,1u128),
                (1,a.clone(),1,2),
                (2,b.clone(),0,3)
            ]{
                let leaf=pallet_zk_tree::ZkLeaf{
                    to:who.clone(),transfer_count:seq,
                    asset_id:0u32,amount:value
                };
                let same_tree=pallet_zk_tree::tree::hash_leaf_native_v2::<Test>(&leaf)
                    .expect("native V2 reference leaf");
                // AccountId32 implements multiple AsRef variants: select bytes.
                let account_bytes:[u8;32]=
                    <AccountId32 as AsRef<[u8]>>::as_ref(&who).try_into().unwrap();
                let from_components=pallet_zk_tree::tree::dvn_native_v2_commitment_from_receipt(
                    account_bytes,seq,value).unwrap();
                assert_eq!(same_tree,from_components,
                    "custody receipt must match exactly the proof stack's V2 leaf hash");
                assert_eq!(DvnV2EscrowCommitment::<Test>::get(id),Some(same_tree));
            }
            assert_ne!(DvnV2EscrowCommitment::<Test>::get(0),
                       DvnV2EscrowCommitment::<Test>::get(1));
            assert_ne!(DvnV2EscrowCommitment::<Test>::get(1),
                       DvnV2EscrowCommitment::<Test>::get(2));
            assert_eq!(DvnV2EscrowTotal::<Test>::get(),6);
            assert_eq!(DvnV2EscrowNextReceipt::<Test>::get(),3);
            assert_eq!(Balances::total_issuance(),count);
            assert_eq!(ZkTree::leaf_count(),0,"separate V2 commitments do not invent V1 Merkle leaves");
        });
    }
    #[test]
    fn dvn_v2_deposit_component_hash_rejects_noncanonical_zero_and_oversupply(){
        use pallet_zk_tree::tree::dvn_native_v2_commitment_from_receipt as hash;
        assert!(hash([3u8;32],0,1).is_ok());
        assert_ne!(hash([3u8;32],0,1).unwrap(),hash([3u8;32],1,1).unwrap());
        assert_ne!(hash([3u8;32],0,1).unwrap(),hash([3u8;32],0,2).unwrap());
        assert!(hash([255u8;32],0,1).is_err());
        assert!(hash([3u8;32],0,0).is_err());
        assert!(hash([3u8;32],0,10_000_000_000_000_001).is_err());
    }
    #[test]
    fn dvn_v2_deposit_failed_debit_creates_no_poseidon_commitment(){
        let sender=account_id(1);
        let vault=Wormhole::devnira_v2_custody_escrow_account();
        new_test_ext_with_endowments(vec![
            (sender.clone(),1000*UNIT),(vault.clone(),10*UNIT)
        ]).execute_with(||{
            let before=Balances::balance(&vault);
            assert!(Wormhole::devnira_v2_record_native_escrow_internal(
                &account_id(99399),&owner(),UNIT).is_err());
            assert_eq!(Balances::balance(&vault),before);
            assert!(DvnV2EscrowCommitment::<Test>::get(0).is_none());
            assert!(DvnV2EscrowReceipt::<Test>::get(0).is_none());
            assert_eq!(DvnV2EscrowTotal::<Test>::get(),0);
        });
    }
'''
def once(s,old,new,label):
    if s.count(old)!=1:
        raise ValueError("STOP: exact upstream composition drift at "+label)
    return s.replace(old,new,1)
def patch(root:Path):
    tree=root/"pallets/zk-tree/src/tree.rs"
    lib=root/"pallets/wormhole/src/lib.rs"
    tests=root/"pallets/wormhole/src/tests.rs"
    original_tree=tree.read_text(encoding="utf-8")
    original_lib=lib.read_text(encoding="utf-8")
    original_tests=tests.read_text(encoding="utf-8")
    if TREE_MARKER in original_tree or LEDGER_MARKER in original_lib:
        raise ValueError("STOP: V2 receipt leaf commitments already installed")
    if "pub fn hash_leaf_native_v2<T: Config>(" not in original_tree:
        raise ValueError("STOP: exact native V2 Poseidon tree hash missing")
    if "DEVNIRA_V2_NATIVE_ESCROW_BACKING_INTERNAL_NO_DISPATCH" not in original_lib:
        raise ValueError("STOP: independent V2 custody layer missing")
    if "DEVNIRA_V2_NATIVE_ESCROW_CUSTODY_NATIVE_FRAME_TESTS" not in original_tests:
        raise ValueError("STOP: actual Rust native custody tests missing")
    new_tree=once(original_tree,"pub fn hash_leaf_native_v2<T: Config>(",
        COMPONENT_FN+"pub fn hash_leaf_native_v2<T: Config>(","native tree helper")
    new_lib=once(original_lib,
        "    pub type DvnV2EscrowReceipt<T:Config>=\n        StorageMap<_,Twox64Concat,u64,([u8;32],u64,u128),OptionQuery>;\n",
        "    pub type DvnV2EscrowReceipt<T:Config>=\n        StorageMap<_,Twox64Concat,u64,([u8;32],u64,u128),OptionQuery>;\n"+LEDGER_STORAGE,
        "native ledger commitment storage")
    new_lib=once(new_lib,
        "            let amount:BalanceOf<T>=amount_base_units.try_into()",
        """            let commitment=pallet_zk_tree::tree::dvn_native_v2_commitment_from_receipt(
                recipient_bytes,count,amount_base_units)
                .map_err(|_|Error::<T>::InvalidProofPublicInputs)?;
            let amount:BalanceOf<T>=amount_base_units.try_into()""",
        "hash before escrow")
    new_lib=once(new_lib,
        "                    DvnV2EscrowReceipt::<T>::insert(id,(recipient_bytes,count,amount_base_units));",
        """                    DvnV2EscrowReceipt::<T>::insert(id,(recipient_bytes,count,amount_base_units));
                    DvnV2EscrowCommitment::<T>::insert(id,commitment);""",
        "commit atomic receipt and hash")
    new_tests=once(original_tests,
        "        DvnV2EscrowRecipientCount,DvnV2EscrowReceipt};",
        "        DvnV2EscrowRecipientCount,DvnV2EscrowReceipt,DvnV2EscrowCommitment};",
        "Rust imports")
    old="    #[test]\n    fn dvn_v2_deposit_bad_alias_zero_overflow_vault_and_failed_debit_reject(){"
    new_tests=once(new_tests,old,RUST_TEST+old,"real native tests")
    # Validation first; only after all source checks succeed modify outputs.
    tree.write_text(new_tree,encoding="utf-8")
    lib.write_text(new_lib,encoding="utf-8")
    tests.write_text(new_tests,encoding="utf-8")
    print("Staged exact native V2 Poseidon receipt commitments, no finalized history root or SEND.")
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("pinned_frame_root",type=Path)
    patch(p.parse_args().pinned_frame_root)
