#!/usr/bin/env python3
"""Stage non-dispatchable on-chain V2 ABI checks in the REAL FRAME wormhole.

No transfers, proof settlement, nullifier writes, V2 verifier activation or
genesis creation. Checks are necessary but insufficient without actual V2
proof verification, sender authorization and trusted historical Merkle root.
"""
import argparse
from pathlib import Path

MARKER = "DEVNIRA_V2_22_PI_PREFLIGHT_NO_SETTLEMENT"
ABI = {"ASSET_ID_INDEX":0,"OUTPUT_AMOUNT_1_INDEX":1,"OUTPUT_AMOUNT_2_INDEX":2,
       "VOLUME_FEE_BPS_INDEX":3,"NULLIFIER_START_INDEX":4,
       "EXIT_ACCOUNT_1_START_INDEX":8,"EXIT_ACCOUNT_2_START_INDEX":12,
       "BLOCK_HASH_START_INDEX":16,"BLOCK_NUMBER_INDEX":20,"INPUT_AMOUNT_INDEX":21}

RUST = r'''
		/// DEVNIRA_V2_22_PI_PREFLIGHT_NO_SETTLEMENT
		/// NON-DISPATCHABLE read-only preflight. NOT cryptographic verification!
		/// Only call after a pinned, authenticated V2 proof has been verified.
		/// The old 15-public-input experimental proof CANNOT pass this gate.
		pub(crate) fn devnira_v2_leaf_chain_preflight(pis: &[u64]) -> Result<(), Error<T>> {
			const PRIME: u64 = 0xffff_ffff_0000_0001;
			const MAX_NATIVE: u128 = 10_000_000_000_000_000;
			ensure!(pis.len() == 22, Error::<T>::InvalidProofPublicInputs);
			ensure!(pis.iter().all(|v| *v < PRIME), Error::<T>::InvalidProofPublicInputs);
			ensure!(pis[0] == 0, Error::<T>::NonNativeAssetNotSupported);
			ensure!(pis[3] == T::VolumeFeeRateBps::get() as u64,
				Error::<T>::InvalidVolumeFeeRate);
			let input = pis[21] as u128;
			let output1 = pis[1] as u128;
			let output2 = pis[2] as u128;
			let total = output1.checked_add(output2)
				.ok_or(Error::<T>::InvalidProofPublicInputs)?;
			ensure!(input > 0 && input <= MAX_NATIVE, Error::<T>::InvalidProofPublicInputs);
			ensure!(total > 0 && total <= input, Error::<T>::InvalidProofPublicInputs);
			// DVN V2 canonical native fee is floor(input * BPS / 10_000).
			// The original permissive check (outputs <= input) allowed an
			// unbounded fee, including zero fee under a positive BPS rate.
			// Enforce exact integer accounting at the actual FRAME gate.
			// u128 multiplication is safe: input <= 10^16 and BPS <= 10^4.
			let bps = pis[3] as u128;
			ensure!(bps <= 10_000, Error::<T>::InvalidVolumeFeeRate);
			let expected_fee = input.checked_mul(bps)
				.ok_or(Error::<T>::InvalidProofPublicInputs)? / 10_000u128;
			ensure!(
				total.checked_add(expected_fee) == Some(input),
				Error::<T>::InvalidProofPublicInputs
			);
			for (amount,start) in [(output1,8usize),(output2,12usize)] {
				if amount > 0 {
					ensure!(pis[start..start+4].iter().any(|v| *v != 0),
						Error::<T>::InvalidProofPublicInputs);
				}
			}
			let mut nullifier = [0u8;32];
			for (i,limb) in pis[4..8].iter().enumerate() {
				nullifier[8*i..8*i+8].copy_from_slice(&limb.to_le_bytes());
			}
			ensure!(nullifier != [0u8;32], Error::<T>::InvalidProofPublicInputs);
			ensure!(!UsedNullifiers::<T>::contains_key(nullifier),
				Error::<T>::NullifierAlreadyUsed);
			let height: u32 = pis[20].try_into()
				.map_err(|_| Error::<T>::InvalidProofPublicInputs)?;
			// A claim about THIS or a future block is not historical,
			// even if malformed storage or a relayer supplies matching bytes.
			let historical_number = BlockNumberFor::<T>::from(height);
			ensure!(historical_number < frame_system::Pallet::<T>::block_number(),
				Error::<T>::BlockNotFound);
			let known = frame_system::Pallet::<T>::block_hash(historical_number);
			ensure!(known != T::Hash::default(), Error::<T>::BlockNotFound);
			let mut claimed = [0u8;32];
			for (i,limb) in pis[16..20].iter().enumerate() {
				claimed[8*i..8*i+8].copy_from_slice(&limb.to_le_bytes());
			}
			ensure!(known.as_ref() == claimed.as_ref(),
				Error::<T>::InvalidProofPublicInputs);
			Ok(())
		}

'''
TEST_MARKER = "DEVNIRA_V2_PALLET_ABI_STORAGE_TESTS"
TEST = r'''
// DEVNIRA_V2_PALLET_ABI_STORAGE_TESTS
#[cfg(test)]
mod devnira_v2_pallet_abi_tests {
    use crate::mock::*;
    use sp_core::H256;

    fn inputs() -> [u64;22] {
        let mut pis=[0u64;22];
        pis[1]=300_000_001;
        pis[2]=199_799_999;
        pis[3]=4;
        pis[4..8].copy_from_slice(&[77,78,79,80]);
        pis[8]=101; pis[12]=102;
        pis[16..20].copy_from_slice(&[10,11,12,13]);
        pis[20]=1;
        pis[21]=500_000_000;
        pis
    }
    fn pin_actual_block() {
        let mut bytes=[0u8;32];
        for i in 0..4 {
            bytes[8*i..8*i+8].copy_from_slice(&(10+i as u64).to_le_bytes());
        }
        frame_system::BlockHash::<Test>::insert(1u64,H256::from(bytes));
    }
    #[test]
    fn dvn_v2_abi_valid_real_frame_storage_is_read_only() {
        new_test_ext().execute_with(|| {
            System::set_block_number(2);
            pin_actual_block();
            let old=Balances::total_issuance();
            assert!(Wormhole::devnira_v2_leaf_chain_preflight(&inputs()).is_ok());
            assert_eq!(old,Balances::total_issuance());
            let mut n=[0u8;32];
            for i in 0..4{n[8*i..8*i+8].copy_from_slice(&inputs()[4+i].to_le_bytes());}
            assert!(!Wormhole::used_nullifiers(n));
        });
    }
    #[test]
    fn dvn_v2_abi_exact_4bps_fee_and_single_base_unit_rounding() {
        new_test_ext().execute_with(|| {
            System::set_block_number(2);
            pin_actual_block();
            let original=inputs();
            assert!(Wormhole::devnira_v2_leaf_chain_preflight(&original).is_ok());
            let old_issuance=Balances::total_issuance();

            // +1 base unit must round the fee DOWN rather than charge +1.
            let mut rounding=original;
            rounding[21]+=1;
            rounding[2]+=1;
            assert!(Wormhole::devnira_v2_leaf_chain_preflight(&rounding).is_ok());

            // No-free-fee: all input given back to the exits is invalid.
            let mut zero_fee=original;
            zero_fee[2]=199_999_999;
            assert!(Wormhole::devnira_v2_leaf_chain_preflight(&zero_fee).is_err());

            // Missing one base unit of fee, or charging one too many, fails.
            let mut underpaid=original;
            underpaid[2]+=1;
            assert!(Wormhole::devnira_v2_leaf_chain_preflight(&underpaid).is_err());
            let mut overcharged=original;
            overcharged[2]-=1;
            assert!(Wormhole::devnira_v2_leaf_chain_preflight(&overcharged).is_err());

            // A fake 10^10 Quantus V1 amount scale is never accepted.
            let mut old_quantized=original;
            old_quantized[21]=50;
            assert!(Wormhole::devnira_v2_leaf_chain_preflight(&old_quantized).is_err());
            assert_eq!(old_issuance,Balances::total_issuance());
        });
    }
    #[test]
    fn dvn_v2_abi_future_block_hash_cannot_authorize_a_spend() {
        new_test_ext().execute_with(|| {
            System::set_block_number(2);
            pin_actual_block();
            let valid = inputs();
            assert!(Wormhole::devnira_v2_leaf_chain_preflight(&valid).is_ok());
            let hash = frame_system::BlockHash::<Test>::get(1u64);
            frame_system::BlockHash::<Test>::insert(2u64,hash);
            frame_system::BlockHash::<Test>::insert(3u64,hash);
            for forbidden in [2u64,3u64] {
                let mut fake=valid;
                fake[20]=forbidden;
                assert!(Wormhole::devnira_v2_leaf_chain_preflight(&fake).is_err(),
                    "current or future block is never valid historical proof: {forbidden}");
            }
            assert!(Wormhole::devnira_v2_leaf_chain_preflight(&valid).is_ok());
        });
    }
    #[test]
    fn dvn_v2_abi_replay_and_wrong_history_are_rejected() {
        new_test_ext().execute_with(|| {
            System::set_block_number(2);
            let pis=inputs();
            assert!(Wormhole::devnira_v2_leaf_chain_preflight(&pis).is_err());
            pin_actual_block();
            let mut n=[0u8;32];
            for i in 0..4{n[8*i..8*i+8].copy_from_slice(&pis[4+i].to_le_bytes());}
            crate::pallet::UsedNullifiers::<Test>::insert(n,true);
            assert!(Wormhole::devnira_v2_leaf_chain_preflight(&pis).is_err());
        });
    }
    #[test]
    fn dvn_v2_abi_bad_15pi_amount_network_and_nullifiers_rejected() {
        new_test_ext().execute_with(|| {
            System::set_block_number(2);
            pin_actual_block();
            let src=inputs();
            assert!(Wormhole::devnira_v2_leaf_chain_preflight(&src[..15]).is_err());
            for i in [0usize,1,2,3,4,8,12,16,20,21] {
                let mut p=src;
                p[i]=match i {
                    0=>1,1=>500_000_001,2=>500_000_001,3=>5,
                    4=>0xffff_ffff_0000_0001,8|12=>0,16=>77,
                    20=>u64::MAX,21=>1,_=>unreachable!()
                };
                assert!(Wormhole::devnira_v2_leaf_chain_preflight(&p).is_err(),
                    "malformed canonical input field {i} accepted");
            }
            let mut zero=src;
            for x in &mut zero[4..8]{*x=0;}
            assert!(Wormhole::devnira_v2_leaf_chain_preflight(&zero).is_err());
            let mut cap=src;
            cap[21]=10_000_000_000_000_001;
            assert!(Wormhole::devnira_v2_leaf_chain_preflight(&cap).is_err());
        });
    }
}
'''

def patch(root:Path,circuits:Path|None=None)->None:
    file=root/"pallets/wormhole/src/lib.rs"
    test=root/"pallets/wormhole/src/tests.rs"
    original=file.read_text(encoding="utf-8")
    previous=test.read_text(encoding="utf-8")
    if MARKER in original or TEST_MARKER in previous:
        raise ValueError("V2 on-chain preflight already staged")
    for required in ("pub(super) type UsedNullifiers<T: Config>",
                     "pub(crate) fn validate_exit_bundle_common(",
                     "pub fn verify_private_batch("):
        if required not in original:
            raise ValueError("Upstream consensus source changed; stop: "+required)
    anchor="\t\tfn segment_is_inert(segment: &ExitSegment) -> bool {"
    if original.count(anchor)!=1:
        raise ValueError("No unique known FRAME helper insertion point")
    if circuits is not None:
        import re
        abi=(circuits/"wormhole/inputs/src/lib.rs").read_text(encoding="utf-8")
        if "pub const PUBLIC_INPUTS_FELTS_LEN: usize = 22;" not in abi:
            raise ValueError("Noncanonical 22-felt ABI")
        for name,value in ABI.items():
            if re.search(rf"pub const {name}: usize = {value};",abi) is None:
                raise ValueError("Canonical proof ABI drift: "+name)
    file.write_text(original.replace(anchor,RUST+anchor),encoding="utf-8")
    test.write_text(previous+"\n"+TEST,encoding="utf-8")
    print("Staged real FRAME 22-PI admission guard and on-chain storage tests; NOT A LIVE VERIFIER.")

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("chain_source",type=Path)
    a.add_argument("--circuit-source",type=Path)
    x=a.parse_args()
    patch(x.chain_source,x.circuit_source)
