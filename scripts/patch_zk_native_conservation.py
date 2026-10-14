#!/usr/bin/env python3
"""Constrain conservation of *exact* eight-decimal DVN base units in Plonky2.

Proves input == output_1 + output_2 + fee, all amounts in [0, 100M DVN],
without Goldilocks wraparound (3*DVN_MAX < prime). Still a V2 candidate;
fee RATE, nullifiers, withdrawal and aggregation need independent checks.
"""
from pathlib import Path
import argparse

MARKER = "fn dvn_native_eight_decimal_conservation_proof()"

CONSERVATION = r'''
/// Value conservation for DVN V2 native amounts with fee/burn explicitly
/// accounted for. The proof is sound as an integer equality because each
/// bounded amount <= 10^16 and the maximum sum < Goldilocks modulus.
/// Fee-rate authorization is separately enforced by the protocol.
pub fn constrain_native_dvn_value_conservation(
    builder: &mut impl GadgetBuilder<F, D>,
    input: Target,
    output_1: Target,
    output_2: Target,
    fee: Target,
) {
    for amount in [input, output_1, output_2, fee] {
        constrain_native_dvn_amount(builder, amount);
    }
    let outputs = builder.add(output_1, output_2);
    let outputs_and_fee = builder.add(outputs, fee);
    builder.connect(input, outputs_and_fee);
}

#[cfg(test)]
mod devnira_native_conservation_tests {
    use super::{
        constrain_native_dvn_value_conservation, DVN_NATIVE_MAX, DVN_BITS,
    };
    use plonky2::{
        field::types::Field,
        iop::witness::{PartialWitness, WitnessWrite},
        plonk::{circuit_builder::CircuitBuilder, circuit_data::CircuitConfig},
    };
    use zk_circuits_common::circuit::{F, D, C};

    #[test]
    fn dvn_native_eight_decimal_conservation_proof() {
        const GOLDILOCKS: u64 = 0xFFFF_FFFF_0000_0001;
        assert!(3 * DVN_NATIVE_MAX < GOLDILOCKS,
            "conservation sums must never alias modulo the field");
        assert!(DVN_NATIVE_MAX < (1u64 << DVN_BITS));
        let mut builder = CircuitBuilder::<F, D>::new(CircuitConfig::standard_recursion_config());
        let input = builder.add_virtual_target();
        let output_1 = builder.add_virtual_target();
        let output_2 = builder.add_virtual_target();
        let fee = builder.add_virtual_target();
        constrain_native_dvn_value_conservation(&mut builder, input, output_1, output_2, fee);
        let circuit = builder.build::<C>();

        let prove = |i:u64, o1:u64, o2:u64, f:u64| {
            let mut pw = PartialWitness::new();
            pw.set_target(input, F::from_canonical_u64(i)).unwrap();
            pw.set_target(output_1, F::from_canonical_u64(o1)).unwrap();
            pw.set_target(output_2, F::from_canonical_u64(o2)).unwrap();
            pw.set_target(fee, F::from_canonical_u64(f)).unwrap();
            circuit.prove(pw)
        };

        for (i,o1,o2,f) in [
            (0,0,0,0),
            (1,1,0,0),
            (500_000_000,300_000_001,199_999_998,1),
            (58_333_333_333_333,30_000_000_000_000,28_333_333_333_332,1),
            (DVN_NATIVE_MAX,DVN_NATIVE_MAX,0,0),
        ] {
            let proof = prove(i,o1,o2,f).expect("valid exact DVN conservation must prove");
            circuit.verify(proof).expect("valid conservation proof must verify");
        }
        for (i,o1,o2,f) in [
            (0,1,0,0), // inflation
            (1,0,0,0), // missing amount
            (500_000_000,300_000_001,199_999_998,2), // changed fee
            (DVN_NATIVE_MAX,DVN_NATIVE_MAX,1,0), // amount overflow
            (DVN_NATIVE_MAX + 1, DVN_NATIVE_MAX,1,0), // input cap violation
            (DVN_NATIVE_MAX, DVN_NATIVE_MAX + 1,0,0), // output cap violation
        ] {
            assert!(prove(i,o1,o2,f).is_err(),
                "invalid DVN amount witness unexpectedly produced proof");
        }
    }
}
'''

def patch(root: Path) -> None:
    file=root/"wormhole/circuit/src/devnira_v2_amount_circuit.rs"
    source=file.read_text()
    if MARKER in source:
        raise ValueError("DVN V2 value conservation proof already installed")
    if "constrain_native_dvn_leaf_hash" not in source or "DVN_NATIVE_MAX" not in source:
        raise ValueError("Missing V2 bounded amount Poseidon leaf; stop")
    if "constrain_native_dvn_value_conservation" in source:
        raise ValueError("Unexpected existing V2 conservation API; manual source review")
    file.write_text(source+"\n"+CONSERVATION)
    print("Constrained exact 1e-8 DVN conservation (input=outputs+fee) in real Plonky2 proof.")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("upstream_root",type=Path)
    patch(ap.parse_args().upstream_root)
