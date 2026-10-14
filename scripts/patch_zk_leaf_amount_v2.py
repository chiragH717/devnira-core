#!/usr/bin/env python3
"""Inject constrained DEVNIRA V2 native amount targets into the *real* leaf circuit crate.

This module is opt-in. The existing production leaf remains V1 until the
chain, prover, aggregator and verifier use the same circuit artifact.
"""
import argparse
from pathlib import Path

MODULE = r'''//! DVN V2 native amount bound circuit gadget (not yet wired into V1 proofs).
//!
//! Each native amount is encoded as one canonical Goldilocks field element.
//! 100M DVN x 10^8 units = 10^16, under 2^54 and the Goldilocks modulus.
//! The range constraint alone is insufficient: it must also cap at 10^16.
use plonky2::{hash::hash_types::HashOutTarget, iop::target::Target};
use zk_circuits_common::{
    circuit::{F, D},
    gadget_builder::GadgetBuilder,
    gadgets::enforce_target_less_than_const,
};

pub const DVN_NATIVE_MAX: u64 = 10_000_000_000_000_000;
pub const DVN_BITS: usize = 54;

/// Enforce native DVN amount is within [0, 100M DVN], inclusive.
/// This gadget targets 64-bit native Plonky2 builders; a wasm32 circuit
/// builder must use a u64-constant comparator instead of usize.
pub fn constrain_native_dvn_amount(builder: &mut impl GadgetBuilder<F, D>, amount: Target) {
    builder.range_check(amount, DVN_BITS);
    let exclusive = usize::try_from(DVN_NATIVE_MAX + 1)
        .expect("V2 circuit builder requires 64-bit usize");
    enforce_target_less_than_const(builder, amount, exclusive, DVN_BITS);
}

/// Input and both outputs must independently fit within the native DVN cap.
/// Conservation and fee constraints are separate required proof obligations.
pub fn constrain_three_native_dvn_amounts(
    builder: &mut impl GadgetBuilder<F, D>,
    input: Target,
    output_1: Target,
    output_2: Target,
) {
    for amount in [input, output_1, output_2] {
        constrain_native_dvn_amount(builder, amount);
    }
}

/// V2 candidate: Poseidon2 commitment with exact native amount bound.
///
/// Layout must be identical to FRAME pallet-zk-tree::hash_leaf_native_v2:
/// account(4 compact felts), transfer_count(2 u32 limbs), asset_id(u32),
/// amount(single 54-bit native DVN base-unit felt).
/// Not connected to the active V1 leaf circuit or batch aggregator yet.
pub fn constrain_native_dvn_leaf_hash(
    builder: &mut impl GadgetBuilder<F, D>,
    account: [Target; 4],
    transfer_count: [Target; 2],
    asset_id: Target,
    amount: Target,
) -> HashOutTarget {
    for piece in transfer_count.iter().copied().chain(core::iter::once(asset_id)) {
        builder.range_check(piece, 32);
    }
    constrain_native_dvn_amount(builder, amount);
    let felts: alloc::vec::Vec<Target> = account.into_iter()
        .chain(transfer_count)
        .chain(core::iter::once(asset_id))
        .chain(core::iter::once(amount))
        .collect();
    builder.poseidon2_hash_no_pad(felts)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn dvn_bound_is_injectively_representable_in_goldilocks() {
        const P: u64 = 0xFFFF_FFFF_0000_0001;
        assert!(DVN_NATIVE_MAX < P);
        assert!(DVN_NATIVE_MAX < (1u64 << DVN_BITS));
        assert!((1u64 << (DVN_BITS - 1)) < DVN_NATIVE_MAX);
    }
    #[test]
    fn dvn_v2_native_poseidon_leaf_proof_commits_single_base_units() {
        use plonky2::{
            field::types::Field,
            iop::witness::{PartialWitness, WitnessWrite},
            plonk::{circuit_builder::CircuitBuilder, circuit_data::CircuitConfig},
        };
        use zk_circuits_common::circuit::C;

        let mut builder = CircuitBuilder::<F, D>::new(CircuitConfig::standard_recursion_config());
        let account = core::array::from_fn(|_| builder.add_virtual_target());
        let transfer_count = core::array::from_fn(|_| builder.add_virtual_target());
        let asset_id = builder.add_virtual_target();
        let amount = builder.add_virtual_target();
        let hash = constrain_native_dvn_leaf_hash(
            &mut builder, account, transfer_count, asset_id, amount,
        );
        builder.register_public_inputs(&hash.elements);
        let circuit = builder.build::<C>();

        let prove = |value: u64| {
            let mut pw = PartialWitness::new();
            for target in account {
                pw.set_target(target, F::from_canonical_u64(0x1111_1111_1111_1111)).unwrap();
            }
            pw.set_target(transfer_count[0], F::ZERO).unwrap();
            pw.set_target(transfer_count[1], F::from_canonical_u64(7)).unwrap();
            pw.set_target(asset_id, F::from_canonical_u64(5)).unwrap();
            pw.set_target(amount, F::from_canonical_u64(value)).unwrap();
            circuit.prove(pw)
        };
        let at_zero = prove(0).expect("zero DVN must prove");
        let at_one = prove(1).expect("one base unit must prove");
        let at_five = prove(500_000_000).expect("5 DVN must prove");
        let at_five_plus_one = prove(500_000_001).expect("5 DVN +1 unit must prove");
        let at_cap = prove(DVN_NATIVE_MAX).expect("100M DVN cap must prove");
        for proof in [&at_zero, &at_one, &at_five, &at_five_plus_one, &at_cap] {
            circuit.verify((*proof).clone()).expect("valid leaf proof must verify");
        }
        assert_ne!(at_zero.public_inputs, at_one.public_inputs,
            "single DVN base unit must change authenticated Poseidon leaf");
        assert_ne!(at_five.public_inputs, at_five_plus_one.public_inputs);
        assert!(prove(DVN_NATIVE_MAX + 1).is_err(),
            "oversupply leaf must never produce a valid proof");
    }

    /// Actually build a Plonky2 circuit and verify its proof, rather than
    /// trusting source-only checks. Amounts > supply must fail proving.
    #[test]
    fn dvn_v2_amount_constraints_reject_above_supply_in_proof() {
        use plonky2::{
            field::types::Field,
            iop::witness::{PartialWitness, WitnessWrite},
            plonk::{circuit_builder::CircuitBuilder, circuit_data::CircuitConfig},
        };
        use zk_circuits_common::circuit::C;

        let mut builder = CircuitBuilder::<F, D>::new(CircuitConfig::standard_recursion_config());
        let amount = builder.add_virtual_target();
        constrain_native_dvn_amount(&mut builder, amount);
        let data = builder.build::<C>();
        for good in [0u64, 1, 500_000_000, DVN_NATIVE_MAX] {
            let mut pw = PartialWitness::new();
            pw.set_target(amount, F::from_canonical_u64(good)).unwrap();
            let proof = data.prove(pw).expect("valid DVN amount must prove");
            data.verify(proof).expect("valid DVN amount must verify");
        }
        for bad in [DVN_NATIVE_MAX + 1, (1u64 << DVN_BITS) - 1] {
            let mut pw = PartialWitness::new();
            pw.set_target(amount, F::from_canonical_u64(bad)).unwrap();
            assert!(data.prove(pw).is_err(), "out-of-supply amount proved");
        }
    }
}
'''

def patch(root: Path) -> None:
    lib = root / "wormhole/circuit/src/lib.rs"
    module = root / "wormhole/circuit/src/devnira_v2_amount_circuit.rs"
    source = lib.read_text()
    if module.exists() or "pub mod devnira_v2_amount_circuit;" in source:
        raise ValueError("V2 circuit gadget already applied")
    if "pub mod zk_merkle_proof;" not in source:
        raise ValueError("Upstream leaf circuit module changed; manual review required")
    module.write_text(MODULE)
    lib.write_text(source + "\n// Prototype only: V1 leaf proofs are unchanged.\npub mod devnira_v2_amount_circuit;\n")
    print("Injected opt-in DVN bounded native amount gadget into real proof circuit crate.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    patch(parser.parse_args().root)
