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
use plonky2::iop::target::Target;
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
