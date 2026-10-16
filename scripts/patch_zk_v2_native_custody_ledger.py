#!/usr/bin/env python3
"""Native FRAME V2 escrow receipts. NO user extrinsic, NO SEND, NO Merkle claim."""
import argparse
from pathlib import Path

MARKER="DEVNIRA_V2_NATIVE_ESCROW_BACKING_INTERNAL_NO_DISPATCH"
STORAGE=r'''
    // DEVNIRA_V2_NATIVE_ESCROW_RECEIPTS_STORAGE
    // Independent native custody liability, NOT a V2 finalized tree.
    #[pallet::storage]
    pub type DvnV2EscrowTotal<T:Config>=StorageValue<_,u128,ValueQuery>;
    #[pallet::storage]
    pub type DvnV2EscrowNextReceipt<T:Config>=StorageValue<_,u64,ValueQuery>;
    #[pallet::storage]
    pub type DvnV2EscrowRecipientCount<T:Config>=
        StorageMap<_,Blake2_128Concat,[u8;32],u64,ValueQuery>;
    #[pallet::storage]
    pub type DvnV2EscrowReceipt<T:Config>=
        StorageMap<_,Twox64Concat,u64,([u8;32],u64,u128),OptionQuery>;

'''
RUST=r'''
        /// DEVNIRA_V2_NATIVE_ESCROW_BACKING_INTERNAL_NO_DISPATCH
        pub(crate) fn devnira_v2_custody_escrow_account()->
            <T as frame_system::Config>::AccountId {
            use sp_runtime::traits::AccountIdConversion;
            frame_support::PalletId(*b"dvn/v2es").into_account_truncating()
        }

        /// Real native transfer + exact base-unit receipt; all-or-nothing.
        /// INTERNAL ONLY: not authorized by user signature / no callable extrinsic.
        /// No fake V1 leaf and no claim of an authenticated V2 history root.
        pub(crate) fn devnira_v2_record_native_escrow_internal(
            sender:&<T as frame_system::Config>::AccountId,
            recipient:&T::WormholeAccountId,
            amount_base_units:u128,
        )->Result<u64,sp_runtime::DispatchError>{
            use frame_support::{
                storage::{with_transaction,TransactionOutcome},
                traits::{fungible::Inspect,tokens::Preservation},
            };
            const MAX:u128=10_000_000_000_000_000;
            const PRIME:u64=0xffff_ffff_0000_0001;
            ensure!(amount_base_units>0 && amount_base_units<=MAX,
                Error::<T>::InvalidProofPublicInputs);
            let recipient_bytes:[u8;32]=recipient.as_ref().try_into()
                .map_err(|_|Error::<T>::InvalidProofPublicInputs)?;
            ensure!(recipient_bytes.chunks_exact(8).all(|chunk|{
                let limb:[u8;8]=chunk.try_into().expect("length eight");
                u64::from_le_bytes(limb)<PRIME
            }),Error::<T>::InvalidProofPublicInputs);
            let vault=Self::devnira_v2_custody_escrow_account();
            let to_account:<T as frame_system::Config>::AccountId=recipient.clone().into();
            ensure!(*sender!=vault && to_account!=vault,
                Error::<T>::InvalidProofPublicInputs);
            let id=DvnV2EscrowNextReceipt::<T>::get();
            let next=id.checked_add(1).ok_or(Error::<T>::InvalidProofPublicInputs)?;
            let count=DvnV2EscrowRecipientCount::<T>::get(recipient_bytes);
            let next_count=count.checked_add(1).ok_or(Error::<T>::InvalidProofPublicInputs)?;
            // Never overwrite an existing receipt under a forged/stale sequence.
            ensure!(!DvnV2EscrowReceipt::<T>::contains_key(id),
                Error::<T>::InvalidProofPublicInputs);
            let total=DvnV2EscrowTotal::<T>::get().checked_add(amount_base_units)
                .filter(|v|*v<=MAX).ok_or(Error::<T>::InvalidProofPublicInputs)?;
            let amount:BalanceOf<T>=amount_base_units.try_into()
                .map_err(|_|Error::<T>::InvalidProofPublicInputs)?;
            with_transaction(||{
                let result=(||->Result<u64,sp_runtime::DispatchError>{
                    <T::Currency as Mutate<_>>::transfer(
                        sender,&vault,amount,Preservation::Preserve)?;
                    let actual:u128=<T::Currency as Inspect<_>>::balance(&vault).try_into()
                        .map_err(|_|Error::<T>::InvalidProofPublicInputs)?;
                    ensure!(actual>=total,Error::<T>::InvalidProofPublicInputs);
                    DvnV2EscrowReceipt::<T>::insert(id,(recipient_bytes,count,amount_base_units));
                    DvnV2EscrowNextReceipt::<T>::put(next);
                    DvnV2EscrowRecipientCount::<T>::insert(recipient_bytes,next_count);
                    DvnV2EscrowTotal::<T>::put(total);
                    Ok(id)
                })();
                match result{
                    Ok(id)=>TransactionOutcome::Commit(Ok(id)),
                    Err(err)=>TransactionOutcome::Rollback(Err(err)),
                }
            })
        }

'''
TEST=r'''
// DEVNIRA_V2_NATIVE_ESCROW_CUSTODY_NATIVE_FRAME_TESTS
#[cfg(test)]
mod dvn_v2_native_escrow_internal_tests{
    use crate::mock::*;
    use crate::pallet::{DvnV2EscrowTotal,DvnV2EscrowNextReceipt,
        DvnV2EscrowRecipientCount,DvnV2EscrowReceipt};
    use sp_core::crypto::AccountId32;
    use qp_wormhole::TransferProofRecorder;
    // Imported explicitly: pallet-balances exposes balance via FRAME Inspect.
    use frame_support::traits::fungible::Inspect;
    fn owner()->AccountId32{AccountId32::new([3u8;32])}
    #[test]
    fn dvn_v2_deposit_exact_base_unit_native_accounting_no_mint(){
        let sender=account_id(1);
        let vault=Wormhole::devnira_v2_custody_escrow_account();
        new_test_ext_with_endowments(vec![
            (sender.clone(),1000*UNIT),(vault.clone(),10*UNIT)
        ]).execute_with(||{
            let before_issuance=Balances::total_issuance();
            let before_vault=Balances::balance(&vault);
            let before_sender=Balances::balance(&sender);
            assert_eq!(Wormhole::devnira_v2_record_native_escrow_internal(
                &sender,&owner(),1),Ok(0));
            assert_eq!(Wormhole::devnira_v2_record_native_escrow_internal(
                &sender,&owner(),2),Ok(1));
            assert_eq!(Balances::balance(&vault),before_vault+3);
            assert_eq!(Balances::balance(&sender),before_sender-3);
            assert_eq!(Balances::total_issuance(),before_issuance);
            assert_eq!(DvnV2EscrowTotal::<Test>::get(),3);
            assert_eq!(DvnV2EscrowNextReceipt::<Test>::get(),2);
            assert_eq!(DvnV2EscrowRecipientCount::<Test>::get([3u8;32]),2);
            assert_eq!(DvnV2EscrowReceipt::<Test>::get(0),Some(([3u8;32],0,1)));
            assert_eq!(DvnV2EscrowReceipt::<Test>::get(1),Some(([3u8;32],1,2)));
            assert_eq!(ZkTree::leaf_count(),0);
            assert!(!<Wormhole as TransferProofRecorder<AccountId,u32,u128>>
                ::record_transfer_proof(None,sender,vault,1));
            assert_eq!(ZkTree::leaf_count(),0);
        });
    }
    #[test]
    fn dvn_v2_deposit_bad_alias_zero_overflow_vault_and_failed_debit_reject(){
        let sender=account_id(1);
        let vault=Wormhole::devnira_v2_custody_escrow_account();
        new_test_ext_with_endowments(vec![
            (sender.clone(),1000*UNIT),(vault.clone(),10*UNIT)
        ]).execute_with(||{
            let issuance=Balances::total_issuance();
            let before=Balances::balance(&vault);
            for (to,value) in [
                (AccountId32::new([255u8;32]),1),
                (owner(),0),(owner(),10_000_000_000_000_001),
                (vault.clone(),1)
            ]{
                assert!(Wormhole::devnira_v2_record_native_escrow_internal(
                    &sender,&to,value).is_err());
            }
            assert!(Wormhole::devnira_v2_record_native_escrow_internal(
                &vault,&owner(),1).is_err());
            assert!(Wormhole::devnira_v2_record_native_escrow_internal(
                &account_id(99399),&owner(),UNIT).is_err());
            DvnV2EscrowRecipientCount::<Test>::insert([3u8;32],u64::MAX);
            assert!(Wormhole::devnira_v2_record_native_escrow_internal(
                &sender,&owner(),1).is_err());
            DvnV2EscrowRecipientCount::<Test>::remove([3u8;32]);
            DvnV2EscrowNextReceipt::<Test>::put(u64::MAX);
            assert!(Wormhole::devnira_v2_record_native_escrow_internal(
                &sender,&owner(),1).is_err());
            assert_eq!(DvnV2EscrowTotal::<Test>::get(),0);
            assert!(DvnV2EscrowReceipt::<Test>::get(0).is_none());
            assert_eq!(Balances::balance(&vault),before);
            assert_eq!(Balances::total_issuance(),issuance);
        });
    }
    #[test]
    fn dvn_v2_deposit_independent_recipients_and_exact_receipt_order(){
        let sender=account_id(1);
        let vault=Wormhole::devnira_v2_custody_escrow_account();
        new_test_ext_with_endowments(vec![
            (sender.clone(),1000*UNIT),(vault.clone(),10*UNIT)
        ]).execute_with(||{
            let another=AccountId32::new([4u8;32]);
            let issuance=Balances::total_issuance();
            let vault_start=Balances::balance(&vault);
            let sender_start=Balances::balance(&sender);
            assert_eq!(Wormhole::devnira_v2_record_native_escrow_internal(
                &sender,&owner(),11),Ok(0));
            assert_eq!(Wormhole::devnira_v2_record_native_escrow_internal(
                &sender,&another,5),Ok(1));
            assert_eq!(Wormhole::devnira_v2_record_native_escrow_internal(
                &sender,&owner(),7),Ok(2));
            assert_eq!(DvnV2EscrowRecipientCount::<Test>::get([3u8;32]),2);
            assert_eq!(DvnV2EscrowRecipientCount::<Test>::get([4u8;32]),1);
            assert_eq!(DvnV2EscrowReceipt::<Test>::get(0),Some(([3u8;32],0,11)));
            assert_eq!(DvnV2EscrowReceipt::<Test>::get(1),Some(([4u8;32],0,5)));
            assert_eq!(DvnV2EscrowReceipt::<Test>::get(2),Some(([3u8;32],1,7)));
            assert_eq!(DvnV2EscrowNextReceipt::<Test>::get(),3);
            assert_eq!(DvnV2EscrowTotal::<Test>::get(),23);
            assert_eq!(Balances::balance(&vault),vault_start+23);
            assert_eq!(Balances::balance(&sender),sender_start-23);
            assert_eq!(Balances::total_issuance(),issuance);
            assert_eq!(ZkTree::leaf_count(),0);
        });
    }
    #[test]
    fn dvn_v2_deposit_underbacked_vault_and_reused_receipt_fail_atomically(){
        let sender=account_id(1);
        let vault=Wormhole::devnira_v2_custody_escrow_account();
        new_test_ext_with_endowments(vec![
            (sender.clone(),1000*UNIT),(vault.clone(),10*UNIT)
        ]).execute_with(||{
            let before_sender=Balances::balance(&sender);
            let before_vault=Balances::balance(&vault);
            let issuance=Balances::total_issuance();
            // Simulate pre-existing inconsistent liabilities. The transfer
            // MUST roll back when it cannot restore full vault solvency.
            DvnV2EscrowTotal::<Test>::put(before_vault+1);
            assert!(Wormhole::devnira_v2_record_native_escrow_internal(
                &sender,&owner(),1).is_err());
            assert_eq!(Balances::balance(&sender),before_sender);
            assert_eq!(Balances::balance(&vault),before_vault);
            assert_eq!(DvnV2EscrowNextReceipt::<Test>::get(),0);
            assert!(DvnV2EscrowReceipt::<Test>::get(0).is_none());
            DvnV2EscrowTotal::<Test>::kill();
            // A corrupted receipt cursor must NOT overwrite an existing
            // commitment or withdraw more than the original deposit.
            DvnV2EscrowReceipt::<Test>::insert(0,([4u8;32],9,2));
            assert!(Wormhole::devnira_v2_record_native_escrow_internal(
                &sender,&owner(),1).is_err());
            assert_eq!(DvnV2EscrowReceipt::<Test>::get(0),Some(([4u8;32],9,2)));
            assert_eq!(DvnV2EscrowTotal::<Test>::get(),0);
            assert_eq!(DvnV2EscrowNextReceipt::<Test>::get(),0);
            assert_eq!(Balances::balance(&sender),before_sender);
            assert_eq!(Balances::balance(&vault),before_vault);
            assert_eq!(Balances::total_issuance(),issuance);
            assert_eq!(ZkTree::leaf_count(),0);
        });
    }
}
'''
V1_OLD='''\t\t\t\tNone => {
\t\t\t\t\tSelf::record_transfer(T::AssetId::default(), &from, &to, amount);
\t\t\t\t\ttrue
\t\t\t\t},'''
V1_NEW='''\t\t\t\tNone => {
\t\t\t\t\t// V2 vault movements must NOT be falsely recorded in quantized V1 tree.
\t\t\t\t\tlet dest:<T as frame_system::Config>::AccountId=to.clone().into();
\t\t\t\t\tif dest==Self::devnira_v2_custody_escrow_account(){return false;}
\t\t\t\t\tSelf::record_transfer(T::AssetId::default(), &from, &to, amount);
\t\t\t\t\ttrue
\t\t\t\t},'''
def replace_exact(text,old,new,label):
    if text.count(old)!=1:
        raise ValueError("STOP: immutable upstream mismatch "+label)
    return text.replace(old,new,1)
def patch(root:Path):
    lib=root/"pallets/wormhole/src/lib.rs"
    tests=root/"pallets/wormhole/src/tests.rs"
    old=lib.read_text(encoding="utf-8")
    old_tests=tests.read_text(encoding="utf-8")
    if MARKER in old or "DEVNIRA_V2_NATIVE_ESCROW_CUSTODY_NATIVE_FRAME_TESTS" in old_tests:
        raise ValueError("STOP: V2 custody patch already installed")
    for required in ("pub(super) type UsedNullifiers<T: Config>",
                     "type WormholeAccountId: Parameter","pub fn verify_private_batch("):
        if required not in old:
            raise ValueError("STOP: wrong FRAME source "+required)
    code=replace_exact(old,"\t#[pallet::event]\n\t#[pallet::generate_deposit(pub(super) fn deposit_event)]",
                       STORAGE+"\t#[pallet::event]\n\t#[pallet::generate_deposit(pub(super) fn deposit_event)]","storage")
    code=replace_exact(code,"\t\tfn segment_is_inert(segment: &ExitSegment) -> bool {",
                       RUST+"\t\tfn segment_is_inert(segment: &ExitSegment) -> bool {","helper")
    code=replace_exact(code,V1_OLD,V1_NEW,"V1 vault guard")
    lib.write_text(code,encoding="utf-8")
    tests.write_text(old_tests.rstrip()+"\n\n"+TEST,encoding="utf-8")
    print("V2 native custody FRAME staged: no dispatch, no V2 tree proof, NO SEND.")
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("pinned_frame_root",type=Path)
    patch(p.parse_args().pinned_frame_root)
