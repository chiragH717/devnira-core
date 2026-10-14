#!/usr/bin/env python3
"""Inject cross-layer Poseidon2 golden-equivalence tests into the real Plonky2 crate.

Tests the same 8-felt preimage used by FRAME pallet-zk-tree and by the
opt-in DEVNIRA circuit candidate. A mismatch is a hard build failure:
passing native-cap-only proofs is not evidence the hashes match on chain.
"""
import argparse
from pathlib import Path

MARKER = "fn dvn_v2_native_leaf_matches_native_qp_poseidon_core()"

TEST = r'''
#[cfg(test)]
mod devnira_cross_layer_leaf_tests {
    use super::{constrain_native_dvn_leaf_hash, DVN_NATIVE_MAX};
    use plonky2::{
        field::types::{Field, PrimeField64},
        iop::witness::{PartialWitness, WitnessWrite},
        plonk::{circuit_builder::CircuitBuilder, circuit_data::CircuitConfig},
    };
    use qp_poseidon_core::{Goldilocks, hash_to_bytes};
    use zk_circuits_common::circuit::{C, F, D};

    /// Native FRAME hash_leaf_native_v2 uses the same eight felts:
    /// [account limb 0..3, transfer high, transfer low, asset ID, amount].
    fn expected_native_leaf(amount: u64, account_limb: u64, count: u64, asset: u32) -> Vec<u64> {
        let native: Vec<Goldilocks> = [
            account_limb, account_limb, account_limb, account_limb,
            count >> 32, count & 0xffff_ffff, asset as u64, amount,
        ].into_iter().map(Goldilocks::from_u64).collect();
        let digest = hash_to_bytes(&native);
        digest.chunks_exact(8).map(|chunk| {
            u64::from_le_bytes(chunk.try_into().expect("digest chunk"))
        }).collect()
    }

    #[test]
    fn dvn_v2_native_leaf_matches_native_qp_poseidon_core() {
        let mut builder = CircuitBuilder::<F, D>::new(CircuitConfig::standard_recursion_config());
        let account: [plonky2::iop::target::Target; 4] =
            core::array::from_fn(|_| builder.add_virtual_target());
        let transfer_count: [plonky2::iop::target::Target; 2] =
            core::array::from_fn(|_| builder.add_virtual_target());
        let asset = builder.add_virtual_target();
        let amount = builder.add_virtual_target();
        let hash = constrain_native_dvn_leaf_hash(
            &mut builder, account, transfer_count, asset, amount,
        );
        builder.register_public_inputs(&hash.elements);
        let circuit = builder.build::<C>();

        // Test carries across u32 high/low transfer_count boundary as well as
        // 1-unit, 5 DVN, founder vesting quantum and the exact native cap.
        let test_vectors = [
            (0u64, 0x1111_1111_1111_1111u64, 7u64, 5u32),
            (1, 0x1111_1111_1111_1111, 7, 5),
            (500_000_000, 0x1111_1111_1111_1111, 7, 5),
            (500_000_001, 0x1111_1111_1111_1111, 7, 5),
            (58_333_333_333_333, 123_456_789, (1u64 << 32) + 7, 0),
            (DVN_NATIVE_MAX, 0x1111_1111_1111_1111, u64::MAX, u32::MAX),
        ];
        for (value, account_limb, count, asset_id) in test_vectors {
            let mut pw = PartialWitness::new();
            for piece in account {
                pw.set_target(piece, F::from_canonical_u64(account_limb)).unwrap();
            }
            pw.set_target(transfer_count[0], F::from_canonical_u64(count >> 32)).unwrap();
            pw.set_target(transfer_count[1], F::from_canonical_u64(count & 0xffff_ffff)).unwrap();
            pw.set_target(asset, F::from_canonical_u64(asset_id as u64)).unwrap();
            pw.set_target(amount, F::from_canonical_u64(value)).unwrap();
            let proof = circuit.prove(pw).expect("valid native DVN leaf must prove");
            circuit.verify(proof.clone()).expect("native DVN leaf proof must verify");
            let actual: Vec<u64> = proof.public_inputs
                .iter().map(|felt| felt.to_canonical_u64()).collect();
            assert_eq!(actual, expected_native_leaf(value, account_limb, count, asset_id),
                "CRITICAL: native FRAME Poseidon2 commitment differs from Plonky2");
        }
    }
}
'''

def patch(root: Path) -> None:
    path=root/"wormhole/circuit/src/devnira_v2_amount_circuit.rs"
    cargo=root/"wormhole/circuit/Cargo.toml"
    source=path.read_text()
    manifest=cargo.read_text()
    if MARKER in source:
        raise ValueError("DVN V2 cross-layer hash test already installed")
    if "constrain_native_dvn_leaf_hash" not in source or "pub const DVN_NATIVE_MAX" not in source:
        raise ValueError("Native DVN leaf gadget missing; refusing mismatched hash regression test")
    needle="qp-plonky2 = { workspace = true }"
    if manifest.count(needle)!=1 or "qp-poseidon-core = { workspace = true }" in manifest:
        raise ValueError("Unexpected Plonky2 crate dependencies; manual review required")
    # Use the SAME hash implementation as on-chain pallet-zk-tree in the
    # fixture rather than a second mock hashing algorithm.
    cargo.write_text(manifest.replace(
        needle,needle+"\nqp-poseidon-core = { workspace = true }",1
    ))
    path.write_text(source+"\n"+TEST)
    print("Added real Poseidon2 native/Plonky2 hash equivalence proof over six DEVNIRA vectors.")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("upstream_root",type=Path)
    patch(ap.parse_args().upstream_root)
