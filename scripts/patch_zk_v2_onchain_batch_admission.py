#!/usr/bin/env python3
"""Read-only V2 22-felt batch admission checks against REAL FRAME nullifier state.

Adds no dispatchable, proof verifier, payment, mint or nullifier writes.
Actual recursion/fees must be authenticated independently before settlement.
"""
import argparse
from pathlib import Path

MARKER = "DEVNIRA V2 FRAME BATCH GUARD DISTINCT NULLIFIERS NO SETTLEMENT"
TEST_MARKER = "DEVNIRA V2 batch storage admission tests no settlement"

RUST = r'''
		/// DEVNIRA V2 FRAME BATCH GUARD DISTINCT NULLIFIERS NO SETTLEMENT.
		///
		/// This is READ-ONLY admission of a collection of canonical 22-felt
		/// records against real FRAME history and UsedNullifiers. NOT a ZK
		/// verifier! Real recursive private+public proofs, pinned VK and
		/// atomic settlement are required before this can authorize funds.
		pub(crate) fn devnira_v2_batch_chain_preflight(
			batch: &[&[u64]],
		) -> Result<(), Error<T>> {
			const MAX_LEAVES: usize = 64;
			const DVN_MAX_NATIVE: u128 = 10_000_000_000_000_000;
			ensure!(!batch.is_empty() && batch.len() <= MAX_LEAVES,
				Error::<T>::InvalidProofPublicInputs);
			let mut inputs = 0u128;
			let mut outputs = 0u128;
			for (i, pis) in batch.iter().enumerate() {
				// Establish each row is canonical and its nullifier has NOT
				// already been settled in chain storage.
				Self::devnira_v2_leaf_chain_preflight(pis)?;
				// Reject two proofs claiming the SAME nullifier within this
				// transaction. A storage check alone will miss that race.
				for earlier in &batch[..i] {
					ensure!(earlier[4..8] != pis[4..8],
						Error::<T>::NullifierAlreadyUsed);
				}
				// Every valid batch must refer to one actual historical
				// block. This is NOT header-root authentication.
				ensure!(pis[16..21] == batch[0][16..21],
					Error::<T>::InvalidProofPublicInputs);
				inputs = inputs.checked_add(pis[21] as u128)
					.ok_or(Error::<T>::InvalidProofPublicInputs)?;
				let paid = (pis[1] as u128).checked_add(pis[2] as u128)
					.ok_or(Error::<T>::InvalidProofPublicInputs)?;
				outputs = outputs.checked_add(paid)
					.ok_or(Error::<T>::InvalidProofPublicInputs)?;
				ensure!(inputs <= DVN_MAX_NATIVE && outputs <= DVN_MAX_NATIVE,
					Error::<T>::InvalidProofPublicInputs);
			}
			ensure!(outputs <= inputs, Error::<T>::InvalidProofPublicInputs);
			Ok(())
		}

'''
TEST = r'''
// DEVNIRA V2 batch storage admission tests no settlement
#[cfg(test)]
mod devnira_v2_frame_batch_admission_tests {
    use crate::mock::*;
    use sp_core::H256;

    fn inputs(nullifier: [u64;4])->[u64;22] {
        let mut pi=[0u64;22];
        pi[1]=300_000_001;
        pi[2]=199_799_999;
        pi[3]=4;
        pi[4..8].copy_from_slice(&nullifier);
        pi[8]=105;pi[12]=106;
        pi[16..20].copy_from_slice(&[10,11,12,13]);
        pi[20]=1;
        pi[21]=500_000_000;
        pi
    }
    fn historical_block() {
        let mut raw=[0u8;32];
        for i in 0..4 {raw[8*i..8*i+8].copy_from_slice(&(10+i as u64).to_le_bytes());}
        frame_system::BlockHash::<Test>::insert(1u64,H256::from(raw));
    }
    #[test]
    fn dvn_v2_batch_real_storage_two_unique_spends_have_no_side_effects(){
        new_test_ext().execute_with(||{
            System::set_block_number(2);
            historical_block();
            let left=inputs([101,102,103,104]);
            let right=inputs([201,202,203,204]);
            let before=Balances::total_issuance();
            assert!(Wormhole::devnira_v2_batch_chain_preflight(
                &[&left[..],&right[..]]).is_ok());
            assert_eq!(before,Balances::total_issuance());
            let mut n=[0u8;32];
            for (i,v) in left[4..8].iter().enumerate() {
                n[8*i..8*i+8].copy_from_slice(&v.to_le_bytes());
            }
            assert!(!Wormhole::used_nullifiers(n),
                "read-only preflight must never mark a spend or settle a coin");
        });
    }
    #[test]
    fn dvn_v2_batch_refuses_intrabatch_and_persisted_replay(){
        new_test_ext().execute_with(||{
            System::set_block_number(2);
            historical_block();
            let left=inputs([101,102,103,104]);
            let copy=left;
            assert!(Wormhole::devnira_v2_batch_chain_preflight(
                &[&left[..],&copy[..]]).is_err());
            let other=inputs([201,202,203,204]);
            let mut key=[0u8;32];
            for (i,v) in left[4..8].iter().enumerate(){
                key[8*i..8*i+8].copy_from_slice(&v.to_le_bytes());
            }
            crate::pallet::UsedNullifiers::<Test>::insert(key,true);
            assert!(Wormhole::devnira_v2_batch_chain_preflight(
                &[&left[..],&other[..]]).is_err());
        });
    }
    #[test]
    fn dvn_v2_batch_refuses_empty_oversized_cross_block_and_supply_cap(){
        new_test_ext().execute_with(||{
            System::set_block_number(2);
            historical_block();
            let left=inputs([101,102,103,104]);
            assert!(Wormhole::devnira_v2_batch_chain_preflight(&[]).is_err());
            let huge=vec![&left[..];65];
            assert!(Wormhole::devnira_v2_batch_chain_preflight(&huge).is_err());
            let mut right=inputs([201,202,203,204]);
            right[20]=2; // should not mix reference heights
            assert!(Wormhole::devnira_v2_batch_chain_preflight(
                &[&left[..],&right[..]]).is_err());
            let mut large=left;
            large[1]=5_000_000_000_000_000;
            large[2]=1;
            large[21]=5_000_000_000_000_001;
            let mut large2=large;
            large2[4..8].copy_from_slice(&[301,302,303,304]);
            let mut large3=large;
            large3[4..8].copy_from_slice(&[401,402,403,404]);
            assert!(Wormhole::devnira_v2_batch_chain_preflight(
                &[&large[..],&large2[..],&large3[..]]).is_err(),
                "cannot aggregate native inputs beyond 100M DVN coin supply");
        });
    }
}
'''
def patch(root:Path):
    lib=root/"pallets/wormhole/src/lib.rs"
    tests=root/"pallets/wormhole/src/tests.rs"
    old=lib.read_text(encoding="utf-8")
    t=tests.read_text(encoding="utf-8")
    if MARKER in old or TEST_MARKER in t:
        raise ValueError("V2 real FRAME batch admission already applied")
    if "DEVNIRA_V2_22_PI_PREFLIGHT_NO_SETTLEMENT" not in old or (
        "pub(crate) fn devnira_v2_leaf_chain_preflight" not in old):
        raise ValueError("STOP: pinned single-leaf on-chain state preflight absent")
    marker="\t\tfn segment_is_inert(segment: &ExitSegment) -> bool {"
    if old.count(marker)!=1:
        raise ValueError("STOP: original FRAME dispatch admission drift")
    lib.write_text(old.replace(marker,RUST+marker),encoding="utf-8")
    tests.write_text(t+"\n"+TEST,encoding="utf-8")
    print("Bounded 64-leaf batch state preflight with pairwise nullifiers. READ ONLY. NOT SETTLEMENT.")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("pinned_chain",type=Path)
    patch(p.parse_args().pinned_chain)
