#!/usr/bin/env python3
"""Integrate real serialized 22PI recursive proofs with the actual FRAME verifier.

This upgrades the previous PI-only mock bridge: proof bytes MUST pass the
FRAME-compatible qp-plonky2-verifier before any canonical ABI/preflight use.
TEST-ONLY verifier data come from pinned GitHub CI artifacts; no production
key or dispatchable is installed. The V1 chain remains NO SEND.
"""
from pathlib import Path
import argparse

MARKER = "DEVNIRA_V2_FRAME_CRYPTO_PROOF_BYTES_COMPAT_TEST_ONLY"
TEST = r'''
// DEVNIRA_V2_FRAME_CRYPTO_PROOF_BYTES_COMPAT_TEST_ONLY
#[cfg(test)]
mod devnira_v2_realproof_frame_crypto_compat {
    use crate::mock::*;
    use crate::{CommonCircuitData, VerifierCircuitData, VerifierOnlyCircuitData,
                WormholeVerifier, DefaultGateSerializer};
    use qp_wormhole_verifier::{ProofWithPublicInputs, C, D, F};
    use qp_plonky2_verifier::field::types::PrimeField64;
    use sp_core::H256;
    use std::path::{Path,PathBuf};

    fn artifacts()->PathBuf {
        let dir=std::env::var("DEVNIRA_REAL_V2_PROOF_ARTIFACT_DIR")
            .expect("FAIL CLOSED: only pinned real proof artifacts are accepted");
        let path=PathBuf::from(dir);
        assert!(path.is_dir(),"no real cryptographic proof artifact directory");
        path
    }

    fn verify_real(
        dir:&Path, name:&str, expected:usize,
    )->(Vec<u64>,Vec<u8>,WormholeVerifier) {
        let verifier_bytes=std::fs::read(dir.join(format!("{name}-vk.bin")))
            .expect("development VK from actual prover");
        let common_bytes=std::fs::read(dir.join(format!("{name}-common.bin")))
            .expect("development common circuit from actual prover");
        let proof_bytes=std::fs::read(dir.join(format!("{name}-proof.bin")))
            .expect("real recursion proof bytes from actual prover");
        assert!(!proof_bytes.is_empty(),"no proof bytes");
        assert!(proof_bytes.len() <= crate::MAX_PROOF_BYTES,"oversized proof");
        let vk=VerifierOnlyCircuitData::from_bytes(verifier_bytes)
            .expect("FRAME verifier must parse actual pinned native VK");
        let common=CommonCircuitData::from_bytes(common_bytes,&DefaultGateSerializer)
            .expect("FRAME verifier must parse actual pinned native common");
        assert_eq!(common.num_public_inputs,expected,
                   "22PI/24PI/46PI proof ABI changed; unsafe version skew");
        let verifier=WormholeVerifier {
            circuit_data:VerifierCircuitData{verifier_only:vk,common},
        };
        let proof=ProofWithPublicInputs::<F,C,D>::from_bytes(
            proof_bytes.clone(),&verifier.circuit_data.common)
            .expect("FRAME-compatible verifier must deserialize actual proof");
        assert_eq!(proof.to_bytes(),proof_bytes,"noncanonical proof representation");
        assert_eq!(proof.public_inputs.len(),expected);
        verifier.verify(proof.clone())
            .expect("ACTUAL FRAME cryptographic recursive verification FAILED");
        let pis=proof.public_inputs.iter().map(|x|x.to_canonical_u64())
            .collect::<Vec<_>>();
        (pis,proof_bytes,verifier)
    }

    fn rejects_tamper(proof_bytes:&[u8],verifier:&WormholeVerifier) {
        // Change a serialized public input at a non-framing byte, or fail parsing.
        let mut corrupted=proof_bytes.to_vec();
        let offset=corrupted.len()/2;
        corrupted[offset]^=1;
        let rejected=match ProofWithPublicInputs::<F,C,D>::from_bytes(
            corrupted,&verifier.circuit_data.common) {
            Ok(proof) => verifier.verify(proof).is_err(),
            Err(_) => true,
        };
        assert!(rejected,"tampered real recursive proof was incorrectly accepted");
        let mut trailer=proof_bytes.to_vec();
        trailer.extend_from_slice(&[0xde,0xad]);
        let noncanonical=match ProofWithPublicInputs::<F,C,D>::from_bytes(
            trailer.clone(),&verifier.circuit_data.common) {
            Ok(proof) => proof.to_bytes()!=trailer,
            Err(_) => true,
        };
        assert!(noncanonical,"appended junk accepted as canonical proof bytes");
    }

    fn pin_real_frame_history(pis:&[u64]) {
        let mut known=[0u8;32];
        for (i,limb) in pis[16..20].iter().enumerate() {
            known[8*i..8*i+8].copy_from_slice(&limb.to_le_bytes());
        }
        // Only test mock can inject BlockHash; never assume user-input hash
        // implies real finalized DEVNIRA history in production.
        frame_system::BlockHash::<Test>::insert(7u64,H256::from(known));
    }

    #[test]
    fn dvn_v2_realproof_frame_verifies_actual_24pi_recursive_bytes_then_storage() {
        let dir=artifacts();
        let (pis,proof_bytes,verifier)=verify_real(
            &dir,"authenticated-22pi-recursive",24);
        rejects_tamper(&proof_bytes,&verifier);
        assert_eq!(pis[0],0);
        assert_eq!(pis[3],4);
        assert_eq!(pis[20],7);
        assert_eq!(pis[21],500_000_000);
        assert_eq!(pis[22],499_800_000);
        assert_eq!(pis[23],200_000);
        new_test_ext().execute_with(|| {
            System::set_block_number(8);
            pin_real_frame_history(&pis);
            let issuance=Balances::total_issuance();
            assert!(Wormhole::devnira_v2_leaf_chain_preflight(&pis[..22]).is_ok());
            assert_eq!(Balances::total_issuance(),issuance);
            let mut forged=pis[..22].to_vec();
            forged[16]^=1;
            assert!(Wormhole::devnira_v2_leaf_chain_preflight(&forged).is_err());
        });
    }

    #[test]
    fn dvn_v2_realproof_frame_verifies_both_full_depth_spends_one_history() {
        let dir=artifacts();
        let (pis,proof_bytes,verifier)=verify_real(
            &dir,"authenticated-22pi-two-leaf",46);
        rejects_tamper(&proof_bytes,&verifier);
        let left=&pis[0..22];
        let right=&pis[22..44];
        assert_eq!(&left[16..21],&right[16..21],
                   "two genuine 22PI spends must reference one historical header");
        assert_ne!(&left[4..8],&right[4..8],
                   "two real leaves cannot use the same nullifier");
        assert_eq!(pis[44],999_600_000);
        assert_eq!(pis[45],400_000);
        new_test_ext().execute_with(|| {
            System::set_block_number(8);
            pin_real_frame_history(left);
            let old=Balances::total_issuance();
            let batch=[left,right];
            assert!(Wormhole::devnira_v2_batch_chain_preflight(&batch).is_ok(),
                    "FRAME batch preflight must accept two proved leaves with shared history");
            let mut nullifier=[0u8;32];
            for (i,limb) in left[4..8].iter().enumerate() {
                nullifier[8*i..8*i+8].copy_from_slice(&limb.to_le_bytes());
            }
            assert!(!Wormhole::used_nullifiers(nullifier));
            crate::pallet::UsedNullifiers::<Test>::insert(nullifier,true);
            assert!(Wormhole::devnira_v2_batch_chain_preflight(&batch).is_err(),
                    "actual storage replay must reject used nullifier");
            assert_eq!(Balances::total_issuance(),old,
                       "no unauthorized settlement in compatibility test");
        });
    }
}
'''

def patch(root:Path)->None:
    tests=root/"pallets/wormhole/src/tests.rs"
    lib=root/"pallets/wormhole/src/lib.rs"
    if not tests.is_file() or not lib.is_file():
        raise ValueError("STOP: pinned real FRAME pallet missing")
    src=lib.read_text(encoding="utf-8")
    if "DEVNIRA_V2_22_PI_PREFLIGHT_NO_SETTLEMENT" not in src or (
        "DEVNIRA V2 FRAME BATCH GUARD DISTINCT NULLIFIERS NO SETTLEMENT" not in src
    ):
        raise ValueError("STOP: real FRAME 22PI leaf+batch state guards missing")
    old=tests.read_text(encoding="utf-8")
    if MARKER in old:
        raise ValueError("STOP: actual proof-byte compatibility tests already installed")
    if "DEVNIRA_V2_REAL_PROVEN_22PI_FRAME_ABI_READ_ONLY_BRIDGE" not in old:
        raise ValueError("STOP: real proof PI history bridge missing")
    tests.write_text(old.rstrip()+"\n\n"+TEST,encoding="utf-8")
    print("FRAME crypto compatibility tests installed: actual native proof bytes, recursive VK and canonical ABI.")
    print("NO: user dispatchable, approved mainnet VK, atomic balance settlement or independent genesis.")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("pinned_chain",type=Path)
    patch(p.parse_args().pinned_chain)
