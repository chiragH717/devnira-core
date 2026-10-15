#!/usr/bin/env python3
"""Test an authenticated, all-or-nothing 8-decimal FRAME V2 escrow payout.

Injects a test-only FRAME execution path into the exact pinned wormhole pallet:
real native 24PI/46PI bytes -> real Plonky2 verification -> canonical ABI/
history/replay checks -> transactional pre-funded escrow transfer + fee +
nullifier persistence. No V1 minting or user-facing extrinsic is enabled.

DO NOT ACTIVATE IN PRODUCTION: development VK, mocked block history, inherited
V1 tree quantization and no independent economic deposit conservation.
"""
import argparse
from pathlib import Path

MARKER = "DEVNIRA_V2_ATOMIC_ESCROW_TEST_ONLY_CRYPTO_PROOF_BEFORE_PAYOUT"
TEST_MARKER = "DEVNIRA_V2_ATOMIC_ESCROW_REAL_CRYPTO_ECONOMICS_TESTS"

RUST = r'''
		/// DEVNIRA_V2_ATOMIC_ESCROW_TEST_ONLY_CRYPTO_PROOF_BEFORE_PAYOUT
		///
		/// Development-only execution proof, EXCLUDED from runtime/WASM via
		/// cfg(test): callers can pass development verifier keys, so this
		/// MUST NEVER be reachable by an extrinsic. Future production
		/// settlement requires a compiled, audited, immutable VK commitment,
		/// DEVNIRA-finalized state-root authentication and funded deposit pool.
		///
		/// 1) Verify REAL proof bytes with qp-plonky2-verifier, including
		///    canonical exact framing and 24PI/46PI aggregate totals.
		/// 2) Check actual FRAME BlockHash, fee, amount and nullifier state.
		/// 3) Transfer from a prefunded test escrow with NO MINTING and
		///    atomically persist used nullifiers only on full success.
		#[cfg(test)]
		pub(crate) fn devnira_v2_settle_verified_escrow_test_only(
			proof_bytes: &[u8],
			verifier: &crate::WormholeVerifier,
			leaves: usize,
			escrow: &<T as frame_system::Config>::AccountId,
			fee_receiver: &<T as frame_system::Config>::AccountId,
		) -> Result<(), sp_runtime::DispatchError> {
			use qp_plonky2_verifier::field::types::PrimeField64;
			use frame_support::{
				storage::{with_transaction, TransactionOutcome},
				traits::tokens::Preservation,
			};

			ensure!(leaves == 1 || leaves == 2, Error::<T>::InvalidProofPublicInputs);
			ensure!(!proof_bytes.is_empty() && proof_bytes.len() <= crate::MAX_PROOF_BYTES,
				Error::<T>::ProofTooLarge);
			let expected_pi = 22usize.checked_mul(leaves).and_then(|n| n.checked_add(2))
				.ok_or(Error::<T>::InvalidProofPublicInputs)?;
			ensure!(verifier.circuit_data.common.num_public_inputs == expected_pi,
				Error::<T>::InvalidProofPublicInputs);
			let proof = ProofWithPublicInputs::<F, C, D>::from_bytes(
				proof_bytes.to_vec(), &verifier.circuit_data.common,
			).map_err(|_| Error::<T>::ProofDeserializationFailed)?;
			ensure!(proof.to_bytes().as_slice() == proof_bytes,
				Error::<T>::NonCanonicalProofEncoding);
			// No balances/nullifiers can be touched until cryptographic
			// verification succeeds. Caller-supplied test VK is untrusted:
			// this entire entrypoint is cfg(test), NEVER runtime executable.
			verifier.verify(proof.clone()).map_err(|_|
				Error::<T>::ProofVerificationFailed)?;
			let pis: Vec<u64> = proof.public_inputs.iter().map(
				|v| v.to_canonical_u64()
			).collect();
			ensure!(pis.len() == expected_pi, Error::<T>::InvalidProofPublicInputs);
			let batch: Vec<&[u64]> = pis[..22*leaves].chunks_exact(22).collect();
			let mut summed_outputs = 0u128;
			let mut summed_fees = 0u128;
			let mut summed_inputs = 0u128;
			for row in &batch {
				let p1 = row[1] as u128;
				let p2 = row[2] as u128;
				let input = row[21] as u128;
				let output = p1.checked_add(p2)
					.ok_or(Error::<T>::InvalidProofPublicInputs)?;
				summed_outputs = summed_outputs.checked_add(output)
					.ok_or(Error::<T>::InvalidProofPublicInputs)?;
				summed_fees = summed_fees.checked_add(input.checked_sub(output)
					.ok_or(Error::<T>::InvalidProofPublicInputs)?)
					.ok_or(Error::<T>::InvalidProofPublicInputs)?;
				summed_inputs = summed_inputs.checked_add(input)
					.ok_or(Error::<T>::InvalidProofPublicInputs)?;
			}
			// Never let untrusted caller-supplied totals or replayed leaves
			// authorize a different output/fee conservation equation.
			ensure!(pis[22*leaves] as u128 == summed_outputs,
				Error::<T>::InvalidProofPublicInputs);
			ensure!(pis[22*leaves+1] as u128 == summed_fees,
				Error::<T>::InvalidProofPublicInputs);
			ensure!(summed_outputs.checked_add(summed_fees) == Some(summed_inputs),
				Error::<T>::InvalidProofPublicInputs);
			// Test escrow is DEMO-FUNDED, NOT genuine independent chain
			// deposit custody. This logic does not create spendable DVN.
			ensure!(escrow != fee_receiver, Error::<T>::InvalidProofPublicInputs);

			// All storage writes (including FRAME Balance events and each
			// nullifier) commit as one unit or fully roll back on any error.
			with_transaction(|| {
				let settle = (|| -> Result<(), sp_runtime::DispatchError> {
					Self::devnira_v2_batch_chain_preflight(&batch)?;
					for row in &batch {
						let mut spent = [0u8;32];
						for (i,limb) in row[4..8].iter().enumerate() {
							spent[8*i..8*i+8].copy_from_slice(&limb.to_le_bytes());
						}
						// Every nullifier is marked before transfers, but all
						// writes roll back on ANY downstream failure.
						UsedNullifiers::<T>::insert(spent, true);
						for (amount_idx,account_start) in [(1usize,8usize),(2usize,12usize)] {
							let amount = row[amount_idx] as u128;
							if amount == 0 { continue; }
							let mut address = [0u8;32];
							for (i,limb) in row[account_start..account_start+4]
								.iter().enumerate() {
								address[8*i..8*i+8].copy_from_slice(&limb.to_le_bytes());
							}
							let target = <T as frame_system::Config>::AccountId::decode(
								&mut &address[..]
							).map_err(|_| Error::<T>::InvalidProofPublicInputs)?;
							ensure!(target != *escrow, Error::<T>::InvalidProofPublicInputs);
							let value: BalanceOf<T> = amount.try_into()
								.map_err(|_| Error::<T>::InvalidProofPublicInputs)?;
							<T::Currency as Mutate<_>>::transfer(
								escrow, &target, value, Preservation::Preserve
							)?;
						}
					}
					if summed_fees > 0 {
						let fee: BalanceOf<T> = summed_fees.try_into()
							.map_err(|_| Error::<T>::InvalidProofPublicInputs)?;
						<T::Currency as Mutate<_>>::transfer(
							escrow, fee_receiver, fee, Preservation::Preserve
						)?;
					}
					Ok(())
				})();
				match settle {
					Ok(()) => TransactionOutcome::Commit(Ok(())),
					Err(err) => TransactionOutcome::Rollback(Err(err)),
				}
			})
		}

'''

TEST = r'''
// DEVNIRA_V2_ATOMIC_ESCROW_REAL_CRYPTO_ECONOMICS_TESTS
#[cfg(test)]
mod devnira_v2_real_crypto_atomic_escrow_tests {
	use crate::mock::*;
	use crate::{CommonCircuitData,VerifierCircuitData,VerifierOnlyCircuitData,
		WormholeVerifier,DefaultGateSerializer};
	use qp_wormhole_verifier::{ProofWithPublicInputs,C,D,F};
	use qp_plonky2_verifier::field::types::PrimeField64;
	use frame_support::traits::fungible::Inspect;
	use sp_core::{H256,crypto::AccountId32};
	use std::path::PathBuf;

	fn real_proof(leaves:usize)->(Vec<u8>,WormholeVerifier,Vec<u64>) {
		let root=PathBuf::from(std::env::var("DEVNIRA_REAL_V2_PROOF_ARTIFACT_DIR")
			.expect("must use genuine native prover artifacts"));
		let name=if leaves==1{"authenticated-22pi-recursive"}
			else{"authenticated-22pi-two-leaf"};
		let bytes=std::fs::read(root.join(format!("{name}-proof.bin")))
			.expect("real serialized 22PI recursive proof");
		let vk=VerifierOnlyCircuitData::from_bytes(
			std::fs::read(root.join(format!("{name}-vk.bin"))).unwrap()).unwrap();
		let common=CommonCircuitData::from_bytes(
			std::fs::read(root.join(format!("{name}-common.bin"))).unwrap(),
			&DefaultGateSerializer).unwrap();
		let verifier=WormholeVerifier {
			circuit_data:VerifierCircuitData{verifier_only:vk,common},
		};
		let decoded=ProofWithPublicInputs::<F,C,D>::from_bytes(
			bytes.clone(),&verifier.circuit_data.common).unwrap();
		assert_eq!(decoded.to_bytes(),bytes);
		verifier.verify(decoded.clone()).expect("native proof rejected by FRAME");
		let pis=decoded.public_inputs.iter().map(|v|v.to_canonical_u64())
			.collect::<Vec<_>>();
		(bytes,verifier,pis)
	}

	fn historical_mock(pis:&[u64]) {
		System::set_block_number(8);
		let mut bytes=[0u8;32];
		for (i,limb) in pis[16..20].iter().enumerate() {
			bytes[8*i..8*i+8].copy_from_slice(&limb.to_le_bytes());
		}
		// NOT finalized real DVN history; ONLY a storage mock!
		frame_system::BlockHash::<Test>::insert(7u64,H256::from(bytes));
	}

	fn receiver(row:&[u64], start:usize)->AccountId32 {
		let mut bytes=[0u8;32];
		for (i,limb) in row[start..start+4].iter().enumerate(){
			bytes[8*i..8*i+8].copy_from_slice(&limb.to_le_bytes());
		}
		AccountId32::from(bytes)
	}

	fn nullifier(row:&[u64])->[u8;32] {
		let mut bytes=[0u8;32];
		for (i,limb) in row[4..8].iter().enumerate(){
			bytes[8*i..8*i+8].copy_from_slice(&limb.to_le_bytes());
		}
		bytes
	}

	#[test]
	fn dvn_v2_crypto_real_escrow_one_leaf_pays_exact_amount_fee_and_one_nullifier() {
		let (bytes,verifier,pis)=real_proof(1);
		let escrow=account_id(91530);
		let fees=account_id(91531);
		let prefund=1_000_000_000u128;
		new_test_ext_with_endowments(vec![(escrow.clone(),prefund)]).execute_with(||{
			historical_mock(&pis);
			let before_issuance=Balances::total_issuance();
			let a=receiver(&pis,8);
			let b=receiver(&pis,12);
			assert_ne!(a,b);
			assert_ne!(a,escrow);
			assert_ne!(b,escrow);
			assert_eq!(Balances::balance(&a),0);
			assert_eq!(Balances::balance(&b),0);
			assert!(Wormhole::devnira_v2_settle_verified_escrow_test_only(
				&bytes,&verifier,1,&escrow,&fees).is_ok(),
				"real 24PI cryptographic proof must unlock prefunded test escrow");
			assert_eq!(Balances::free_balance(&a),pis[1] as u128);
			assert_eq!(Balances::free_balance(&b),pis[2] as u128);
			assert_eq!(Balances::free_balance(&fees),200_000);
			assert_eq!(Balances::free_balance(&escrow),prefund-pis[21] as u128);
			assert!(Wormhole::used_nullifiers(nullifier(&pis)));
			assert_eq!(Balances::total_issuance(),before_issuance,
				"escrow-native payout may NOT mint one base unit");
			let before=(Balances::free_balance(&a),Balances::free_balance(&b),
				Balances::free_balance(&fees));
			assert!(Wormhole::devnira_v2_settle_verified_escrow_test_only(
				&bytes,&verifier,1,&escrow,&fees).is_err(),"replay must fail");
			assert_eq!(before,(Balances::free_balance(&a),
				Balances::free_balance(&b),Balances::free_balance(&fees)));
		});
	}

	#[test]
	fn dvn_v2_crypto_real_escrow_two_leaf_atomic_exact_fee_and_replay() {
		let (bytes,verifier,pis)=real_proof(2);
		let escrow=account_id(91532);
		let fees=account_id(91533);
		let prefund=2_000_000_000u128;
		new_test_ext_with_endowments(vec![(escrow.clone(),prefund)]).execute_with(||{
			historical_mock(&pis);
			let old=Balances::total_issuance();
			assert_eq!(&pis[16..21],&pis[38..43]);
			let n1=nullifier(&pis[..22]);
			let n2=nullifier(&pis[22..44]);
			assert_ne!(n1,n2);
			assert!(Wormhole::devnira_v2_settle_verified_escrow_test_only(
				&bytes,&verifier,2,&escrow,&fees).is_ok());
			assert!(Wormhole::used_nullifiers(n1));
			assert!(Wormhole::used_nullifiers(n2));
			assert_eq!(Balances::free_balance(&escrow),prefund-1_000_000_000);
			assert_eq!(Balances::free_balance(&fees),400_000);
			let a=receiver(&pis,8);
			let b=receiver(&pis,12);
			assert_eq!(Balances::free_balance(&a),2*pis[1] as u128);
			assert_eq!(Balances::free_balance(&b),2*pis[2] as u128);
			assert_eq!(Balances::total_issuance(),old);
			assert!(Wormhole::devnira_v2_settle_verified_escrow_test_only(
				&bytes,&verifier,2,&escrow,&fees).is_err());
			assert_eq!(Balances::total_issuance(),old);
			assert_eq!(Balances::free_balance(&fees),400_000);
		});
	}

	#[test]
	fn dvn_v2_crypto_escrow_insufficient_funds_rolls_back_partial_payout_and_nullifier() {
		let (bytes,verifier,pis)=real_proof(1);
		let escrow=account_id(91534);
		let fees=account_id(91535);
		// First 300000001 transfer can succeed, but second 199799999
		// would violate vault keep-alive. Rollback MUST undo first credit.
		let prefund=400_000_000u128;
		new_test_ext_with_endowments(vec![(escrow.clone(),prefund)]).execute_with(||{
			historical_mock(&pis);
			let a=receiver(&pis,8);
			let b=receiver(&pis,12);
			let old=Balances::total_issuance();
			assert!(Wormhole::devnira_v2_settle_verified_escrow_test_only(
				&bytes,&verifier,1,&escrow,&fees).is_err());
			assert!(!Wormhole::used_nullifiers(nullifier(&pis)));
			assert_eq!(Balances::free_balance(&a),0,"first credit MUST roll back");
			assert_eq!(Balances::free_balance(&b),0);
			assert_eq!(Balances::free_balance(&fees),0);
			assert_eq!(Balances::free_balance(&escrow),prefund);
			assert_eq!(Balances::total_issuance(),old);
		});
	}

	#[test]
	fn dvn_v2_crypto_escrow_tamper_wrong_history_and_trailing_bytes_fail_closed() {
		let (bytes,verifier,pis)=real_proof(1);
		let escrow=account_id(91536);
		let fees=account_id(91537);
		new_test_ext_with_endowments(vec![(escrow.clone(),1_000_000_000)]).execute_with(||{
			historical_mock(&pis);
			let old=Balances::total_issuance();
			let mut bad=bytes.clone();
			let corruption_offset=bad.len()/2;
			bad[corruption_offset]^=1;
			assert!(Wormhole::devnira_v2_settle_verified_escrow_test_only(
				&bad,&verifier,1,&escrow,&fees).is_err());
			let mut junk=bytes.clone();
			junk.extend_from_slice(&[0x01,0x02]);
			assert!(Wormhole::devnira_v2_settle_verified_escrow_test_only(
				&junk,&verifier,1,&escrow,&fees).is_err());
			assert!(Wormhole::devnira_v2_settle_verified_escrow_test_only(
				&bytes,&verifier,2,&escrow,&fees).is_err());
			frame_system::BlockHash::<Test>::remove(7u64);
			assert!(Wormhole::devnira_v2_settle_verified_escrow_test_only(
				&bytes,&verifier,1,&escrow,&fees).is_err());
			assert!(!Wormhole::used_nullifiers(nullifier(&pis)));
			assert_eq!(Balances::total_issuance(),old);
			assert_eq!(Balances::free_balance(&escrow),1_000_000_000);
		});
	}
}
'''

def patch(root:Path)->None:
    lib=root/"pallets/wormhole/src/lib.rs"
    tests=root/"pallets/wormhole/src/tests.rs"
    if not lib.is_file() or not tests.is_file():
        raise ValueError("STOP: real pinned FRAME wormhole source is required")
    before=lib.read_text(encoding="utf-8")
    old_tests=tests.read_text(encoding="utf-8")
    if MARKER in before or TEST_MARKER in old_tests:
        raise ValueError("STOP: authenticated atomic escrow test already staged")
    for anchor in (
        "DEVNIRA_V2_22_PI_PREFLIGHT_NO_SETTLEMENT",
        "DEVNIRA V2 FRAME BATCH GUARD DISTINCT NULLIFIERS NO SETTLEMENT",
        "fn segment_is_inert(segment: &ExitSegment) -> bool {",
    ):
        if anchor not in before:
            raise ValueError("STOP: required checked FRAME state gate missing: "+anchor)
    if "DEVNIRA_V2_FRAME_CRYPTO_PROOF_BYTES_COMPAT_TEST_ONLY" not in old_tests:
        raise ValueError("STOP: prior real proof-byte verifier tests are absent")
    anchor="\t\tfn segment_is_inert(segment: &ExitSegment) -> bool {"
    if before.count(anchor)!=1:
        raise ValueError("STOP: pinned wormhole test placement has changed")
    lib.write_text(before.replace(anchor,RUST+anchor),encoding="utf-8")
    tests.write_text(old_tests.rstrip()+"\n\n"+TEST,encoding="utf-8")
    print("STAGED: real Plonky2 proof-byte gated, test-only FRAME escrow balances + fees + persistent replay nullifiers under ONE storage transaction.")
    print("NOT ACTIVE: no dispatchable, development VK only, no genuine independent deposit/genesis/active signed Send.")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("pinned_chain",type=Path)
    patch(parser.parse_args().pinned_chain)
