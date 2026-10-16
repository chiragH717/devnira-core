#!/usr/bin/env python3
"""Real 24PI PRIVATE + 50PI PUBLIC two-tier Plonky2 to FRAME integration.

The full native prover exports the actual public/private verifier bytes.
FRAME verifies both and exercises test-only atomic escrow settlement,
no user dispatchable / no runtime key activation.
"""
from pathlib import Path
import argparse
MARKER="DEVNIRA_V2_FRAME_PRIVATE_PUBLIC_REAL_FIXED_VK_50PI"
RUST=r'''
// DEVNIRA_V2_FRAME_PRIVATE_PUBLIC_REAL_FIXED_VK_50PI
#[cfg(test)]
mod devnira_v2_private_public_actual_frame_escrow {
    use crate::mock::*;
    use crate::{CommonCircuitData,VerifierCircuitData,VerifierOnlyCircuitData,
        WormholeVerifier,DefaultGateSerializer};
    use qp_wormhole_verifier::{ProofWithPublicInputs,C,D,F};
    use qp_plonky2_verifier::field::types::PrimeField64;
    use sp_core::{H256,crypto::AccountId32};
    use std::path::PathBuf;

    fn actual_proof(name:&str,expected:usize)->(Vec<u8>,WormholeVerifier,Vec<u64>) {
        let root=PathBuf::from(std::env::var("DEVNIRA_REAL_V2_PROOF_ARTIFACT_DIR")
            .expect("STOP: pinned native proof bytes and two-tier VK required"));
        let bytes=std::fs::read(root.join(format!("{name}-proof.bin")))
            .expect("real immutable-job proof bytes missing");
        let vk=VerifierOnlyCircuitData::from_bytes(
            std::fs::read(root.join(format!("{name}-vk.bin"))).unwrap()).unwrap();
        let common=CommonCircuitData::from_bytes(
            std::fs::read(root.join(format!("{name}-common.bin"))).unwrap(),
            &DefaultGateSerializer).unwrap();
        assert_eq!(common.num_public_inputs,expected);
        let verifier=WormholeVerifier {
            circuit_data:VerifierCircuitData{verifier_only:vk,common}
        };
        assert!(!bytes.is_empty() && bytes.len() <= crate::MAX_PROOF_BYTES);
        let decoded=ProofWithPublicInputs::<F,C,D>::from_bytes(
            bytes.clone(),&verifier.circuit_data.common).unwrap();
        assert_eq!(decoded.to_bytes(),bytes,"noncanonical proof bytes must be rejected");
        verifier.verify(decoded.clone()).expect("FRAME actual native recursive proof");
        let pis=decoded.public_inputs.iter().map(|v|v.to_canonical_u64())
            .collect::<Vec<_>>();
        (bytes,verifier,pis)
    }
    fn receiver(row:&[u64],start:usize)->AccountId32 {
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
    fn mock_history(pis:&[u64]) {
        System::set_block_number(8);
        let mut hash=[0u8;32];
        for (i,limb) in pis[16..20].iter().enumerate(){
            hash[8*i..8*i+8].copy_from_slice(&limb.to_le_bytes());
        }
        // TEST-ONLY; production MUST obtain header from actual finalized
        // independent DEVNIRA chain history and prove state-root inclusion.
        frame_system::BlockHash::<Test>::insert(7u64,H256::from(hash));
    }
    #[test]
    fn dvn_v2_private_public_real_private_then_public_frame_and_atomic_replay() {
        let (_,private_verifier,private_pi)=actual_proof("private-v2-24pi",24);
        assert_eq!(private_verifier.circuit_data.common.num_public_inputs,24);
        let (public_bytes,public_vk,public_pi)=actual_proof("public-v2-50pi",50);
        assert_eq!(&public_pi[0..24],private_pi.as_slice(),
            "public aggregate first segment must contain genuine verified PRIVATE proof");
        // Authenticate the independently generated second PRIVATE proof
        // against the SAME fixed PRIVATE verifier key, not synthetic PIs.
        let other_bytes=std::fs::read(PathBuf::from(
            std::env::var("DEVNIRA_REAL_V2_PROOF_ARTIFACT_DIR").unwrap())
            .join("private-v2-24pi-other-proof.bin"))
            .expect("real second private witness proof missing");
        assert!(!other_bytes.is_empty() && other_bytes.len() <= crate::MAX_PROOF_BYTES);
        let other_proof=ProofWithPublicInputs::<F,C,D>::from_bytes(
            other_bytes.clone(),&private_verifier.circuit_data.common).unwrap();
        assert_eq!(other_proof.to_bytes(),other_bytes);
        private_verifier.verify(other_proof.clone())
            .expect("second private proof must verify against the SAME fixed PRIVATE key");
        let second_private_pi=other_proof.public_inputs.iter().map(
            |v|v.to_canonical_u64()).collect::<Vec<_>>();
        assert_eq!(&public_pi[24..48],second_private_pi.as_slice(),
            "public aggregate second segment must contain genuine verified PRIVATE proof");
        assert_eq!(&public_pi[16..21],&public_pi[40..45],
            "all private segments must reference identical historical root");
        assert_ne!(&public_pi[4..8],&public_pi[28..32],
            "public MUST contain distinct real nullifiers");
        assert_eq!(public_pi[48],999_600_000);
        assert_eq!(public_pi[49],400_000);
        let escrow=account_id(91601);
        let miner_fee=account_id(91602);
        let original_funding=2_000_000_000u128;
        new_test_ext_with_endowments(vec![(escrow.clone(),original_funding)])
            .execute_with(|| {
                mock_history(&public_pi);
                let original_supply=Balances::total_issuance();
                assert!(Wormhole::devnira_v2_settle_verified_escrow_test_only(
                    &public_bytes,&public_vk,2,&escrow,&miner_fee).is_ok(),
                    "FRAME must cryptographically verify PUBLIC proof + execute atomic payout");
                assert_eq!(Balances::free_balance(&escrow),original_funding-1_000_000_000);
                assert_eq!(Balances::free_balance(&miner_fee),400_000);
                assert!(Wormhole::used_nullifiers(nullifier(&public_pi[..22])));
                assert!(Wormhole::used_nullifiers(nullifier(&public_pi[24..46])));
                let a=receiver(&public_pi,8);
                let b=receiver(&public_pi,12);
                assert_eq!(Balances::free_balance(&a),2*public_pi[1] as u128);
                assert_eq!(Balances::free_balance(&b),2*public_pi[2] as u128);
                assert_eq!(Balances::total_issuance(),original_supply,
                    "actual test escrow is non-minting; no free money issuance");
                assert!(Wormhole::devnira_v2_settle_verified_escrow_test_only(
                    &public_bytes,&public_vk,2,&escrow,&miner_fee).is_err(),
                    "replay of cryptographically valid PUBLIC proof must not pay");
                assert_eq!(Balances::free_balance(&miner_fee),400_000);
                assert_eq!(Balances::total_issuance(),original_supply);
            });
    }

    #[test]
    fn dvn_v2_private_public_real_no_payout_if_history_missing_or_escrow_underfunded() {
        let (bytes,verifier,pis)=actual_proof("public-v2-50pi",50);
        let escrow=account_id(91603);
        let miner_fee=account_id(91604);
        new_test_ext_with_endowments(vec![(escrow.clone(),400_000_000)])
            .execute_with(|| {
                System::set_block_number(8);
                let old_supply=Balances::total_issuance();
                assert!(Wormhole::devnira_v2_settle_verified_escrow_test_only(
                    &bytes,&verifier,2,&escrow,&miner_fee).is_err(),
                    "absent historic block must reject real cryptographic proof");
                mock_history(&pis);
                let a=receiver(&pis,8);
                let b=receiver(&pis,12);
                assert!(Wormhole::devnira_v2_settle_verified_escrow_test_only(
                    &bytes,&verifier,2,&escrow,&miner_fee).is_err(),
                    "insufficient escrow must atomically roll back all private batches");
                assert!(!Wormhole::used_nullifiers(nullifier(&pis[..22])));
                assert!(!Wormhole::used_nullifiers(nullifier(&pis[24..46])));
                assert_eq!(Balances::free_balance(&escrow),400_000_000);
                assert_eq!(Balances::free_balance(&a),0);
                assert_eq!(Balances::free_balance(&b),0);
                assert_eq!(Balances::free_balance(&miner_fee),0);
                assert_eq!(Balances::total_issuance(),old_supply);
            });
    }
}
'''
def patch(root:Path)->None:
    file=root/"pallets/wormhole/src/tests.rs"
    if not file.is_file():
        raise ValueError("STOP: missing pinned real FRAME source")
    text=file.read_text(encoding="utf-8")
    if MARKER in text:
        raise ValueError("STOP: two-tier private/public already staged")
    for required in ("DEVNIRA_V2_ATOMIC_ESCROW_REAL_CRYPTO_ECONOMICS_TESTS",
       "DEVNIRA_V2_FRAME_CRYPTO_PROOF_BYTES_COMPAT_TEST_ONLY"):
        if required not in text:
            raise ValueError("STOP: authenticated proof-byte escrow missing: "+required)
    file.write_text(text.rstrip()+"\n\n"+RUST,encoding="utf-8")
    print("Two tier private(24PI) + public(50PI) proof-byte FRAME cryptography, escrow balance, replay and rollback tests staged.")
    print("NO on-chain runtime production key, no independent finalized chain history, no signed public transactions.")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("pinned_frame",type=Path)
    patch(p.parse_args().pinned_frame)
