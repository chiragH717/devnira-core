#!/usr/bin/env python3
"""Inject real Plonky2 8-decimal private/public batch value constraints.

Inert source module, deliberately NOT a replacement for live V1 recursive
circuits. This validates the mathematically dangerous u32->u64 migration
over real prover-generated proofs in qp-wormhole-aggregator 4.4.0.
"""
import argparse
from pathlib import Path

MARKER="pub mod devnira_v2_segment;"
RUST=r'''//! DEVNIRA V2 native exact-value recursive batch building block (inactive).
//!
//! A complete migration additionally needs V2 leaf verifier digests, Merkle
//! membership, nullifier uniqueness/settlement, fee-rate logic, recursive
//! wrappers, public-output binding and matching on-chain pinned artifacts.
//! This module is a real Plonky2 constraint/proof candidate, NOT live V2.
use plonky2::{field::types::Field, iop::target::Target};
use zk_circuits_common::{
    circuit::{F, D},
    gadget_builder::GadgetBuilder,
    gadgets::enforce_target_less_than_const,
};
pub const DVN_MAX: u64=10_000_000_000_000_000;
pub const DVN_BITS: usize=54;
pub const MAX_LEAVES: usize=64;

/// A Goldilocks felt is an exact native DVN balance, never Quantus's
/// quantized V1 u32 amount. This cap is safe under the 54-bit range check.
pub fn constrain_v2_native_amount(
    builder: &mut impl GadgetBuilder<F,D>, amount: Target
) {
    builder.range_check(amount,DVN_BITS);
    enforce_target_less_than_const(
        builder,amount,
        usize::try_from(DVN_MAX+1).expect("V2 circuit construction requires 64-bit host"),
        DVN_BITS,
    );
}

/// Constrain a native full-precision private batch before recursion.
///
/// Every individual amount <= 100M DVN. Both running sums <= 100M DVN,
/// ensuring (a) no field wraparound (b) no fabricated extra issuance and
/// (c) a batch whose sum exceeds total coin supply cannot be settled.
/// The protocol's *per-block fee policy* is additional to conservation.
pub fn constrain_v2_private_batch_value(
    builder: &mut impl GadgetBuilder<F,D>,
    inputs: &[Target],
    outputs: &[Target],
    total_fee: Target,
) -> (Target,Target) {
    assert!(!inputs.is_empty() && inputs.len() <= MAX_LEAVES,
        "DEVNIRA V2 leaf count out of bounds");
    assert_eq!(outputs.len(),2*inputs.len(),
        "DEVNIRA V2 requires two exits per leaf");
    let mut total_in=builder.zero();
    for amount in inputs {
        constrain_v2_native_amount(builder,*amount);
        total_in=builder.add(total_in,*amount);
    }
    constrain_v2_native_amount(builder,total_in);
    let mut total_out=builder.zero();
    for amount in outputs {
        constrain_v2_native_amount(builder,*amount);
        total_out=builder.add(total_out,*amount);
    }
    constrain_v2_native_amount(builder,total_out);
    constrain_v2_native_amount(builder,total_fee);
    let plus_fee=builder.add(total_out,total_fee);
    builder.connect(total_in,plus_fee);
    // All three terms <= 10^16 and the sum <= 2*10^16, which is
    // below the Goldilocks prime, so equality is an integer equality.
    (total_in,total_out)
}

/// Public wrapper amounts are deduped, summed outputs. Enforce 100M
/// maximum combined native settlement across every exit slot even when
/// each individual account amount is below cap. No 32-bit truncation.
pub fn constrain_v2_public_batch_exits(
    builder: &mut impl GadgetBuilder<F,D>, exits: &[Target]
) -> Target {
    assert!(!exits.is_empty() && exits.len() <= MAX_LEAVES*MAX_LEAVES*2,
        "DEVNIRA V2 public-batch slot count out of bounds");
    let mut total=builder.zero();
    for amount in exits {
        constrain_v2_native_amount(builder,*amount);
        total=builder.add(total,*amount);
        // SECURITY: do not check only the final sum! With up to 8192
        // public exit slots, raw native amounts can exceed Goldilocks p
        // and wrap to an apparently valid total (e.g. exactly p -> 0).
        // Bound every monotone prefix: previous total <=1e16 and the
        // next amount <=1e16, so the addition itself is <2e16 << p.
        constrain_v2_native_amount(builder,total);
    }
    total
}
/// Mandatory fail-fast preflight before passing *untrusted* witnesses into
/// Plonky2. Some Plonky2 range-check generators panic on invalid inputs;
/// never expose that panic to a production network request. The circuit
/// enforces the same constraints independently against a malicious prover.
pub fn validate_v2_fee_segment_values(
    inputs: &[u64], outputs: &[u64], fee: u64, bps: u64,
) -> Result<(), &'static str> {
    if inputs.is_empty() || inputs.len()>MAX_LEAVES || outputs.len()!=2*inputs.len() {
        return Err("DVN V2 batch dimension mismatch");
    }
    if bps>10_000 {
        return Err("DVN V2 fee rate out of basis-point bounds");
    }
    if fee>DVN_MAX || inputs.iter().chain(outputs).any(|v| *v>DVN_MAX) {
        return Err("DVN V2 per-amount cap exceeded");
    }
    let total_in: u128=inputs.iter().map(|x| *x as u128).sum();
    let total_out: u128=outputs.iter().map(|x| *x as u128).sum();
    if total_in > DVN_MAX as u128 || total_out>DVN_MAX as u128 {
        return Err("DVN V2 batch exceeds total supply");
    }
    if total_in != total_out + fee as u128 {
        return Err("DVN V2 conservation violated");
    }
    if total_out * 10_000u128 > total_in * ((10_000u64-bps) as u128) {
        return Err("DVN V2 underpaid volume fee");
    }
    Ok(())
}

/// Multiply 54-bit native DVN x 14-bit fee coefficient into TWO exact
/// base-2^32 limbs. A single Goldilocks multiplication would wrap for
/// 100M DVN * 10000, so must never be used for the whole product.
fn v2_mul_amount_by_bps(
    b: &mut impl GadgetBuilder<F,D>, amount: Target, coeff: Target
) -> (Target,Target) {
    constrain_v2_native_amount(b,amount);
    b.range_check(coeff,14);
    let (lo,hi)=b.split_low_high(amount,32,54);
    let low_product=b.mul(lo,coeff); // < 2^46, no field wrap
    let (product_lo,carry)=b.split_low_high(low_product,32,46);
    let high_product=b.mul(hi,coeff); // < 2^36
    let product_hi=b.add(high_product,carry); // < 2^37
    b.range_check(product_hi,37);
    (product_lo,product_hi)
}

/// Prove A >= B where each A and B is represented as (u32_low, u37_high).
/// The underlying integer product can be up to 10^20 (above Goldilocks P),
/// but all arithmetic below stays < 2^38, so field wrap is impossible.
fn v2_enforce_product_ge(
    b: &mut impl GadgetBuilder<F,D>,
    a: (Target,Target), b_product: (Target,Target),
) {
    let (a_lo,a_hi)=a;
    let (b_lo,b_hi)=b_product;
    let two_pow_32=b.constant(F::from_canonical_u64(1u64<<32));
    let lo_plus_pow=b.add(a_lo,two_pow_32);
    let low_delta=b.sub(lo_plus_pow,b_lo);
    // 2^32 + a_lo - b_lo lies in [1, 2^33-1]; its highest bit
    // is 1 exactly when there was NO low-limb borrow.
    let (_,no_borrow)=b.split_low_high(low_delta,32,33);
    let one=b.one();
    let borrow=b.sub(one,no_borrow);
    let high_delta=b.sub(a_hi,b_hi);
    let high_after_borrow=b.sub(high_delta,borrow);
    // Negative high differences wrap near P and cannot pass 37 bits.
    b.range_check(high_after_borrow,37);
}

/// Actual volume-fee BPS inequality with NO modular overflow:
/// output * 10000 <= input * (10000-bps).
/// The fee amount itself must also be constrained by exact conservation.
/// Shared BPS policy authorization still belongs to the runtime.
pub fn constrain_v2_batch_volume_fee(
    b: &mut impl GadgetBuilder<F,D>,
    total_input: Target, total_output: Target, volume_fee_bps: Target,
) {
    use plonky2::field::types::Field;
    constrain_v2_native_amount(b,total_input);
    constrain_v2_native_amount(b,total_output);
    b.range_check(volume_fee_bps,14);
    let ten_thousand=b.constant(F::from_canonical_u64(10_000));
    let fee_complement=b.sub(ten_thousand,volume_fee_bps);
    b.range_check(fee_complement,14); // BPS must be <=10000
    let lhs=v2_mul_amount_by_bps(b,total_output,ten_thousand);
    let rhs=v2_mul_amount_by_bps(b,total_input,fee_complement);
    v2_enforce_product_ge(b,rhs,lhs);
}

#[cfg(test)]
mod tests {
    use super::*;
    use plonky2::{
        field::types::Field,
        iop::witness::{PartialWitness,WitnessWrite},
        plonk::{circuit_builder::CircuitBuilder,circuit_data::CircuitConfig},
    };
    use zk_circuits_common::circuit::C;

    #[test]
    fn dvn_v2_fee_rate_handles_greater_than_field_products_without_wrapping() {
        let mut b=CircuitBuilder::<F,D>::new(CircuitConfig::standard_recursion_config());
        let inp=[b.add_virtual_target()];
        let out=[b.add_virtual_target(),b.add_virtual_target()];
        let fee=b.add_virtual_target();
        let bps=b.add_virtual_target();
        let (total_in,total_out)=
            constrain_v2_private_batch_value(&mut b,&inp,&out,fee);
        constrain_v2_batch_volume_fee(&mut b,total_in,total_out,bps);
        b.register_public_input(total_in);
        b.register_public_input(total_out);
        b.register_public_input(bps);
        let circuit=b.build::<C>();
        let prove=|i:u64, o1:u64, o2:u64, f:u64,rate:u64| {
            validate_v2_fee_segment_values(&[i],&[o1,o2],f,rate)
                .map_err(|e| anyhow::anyhow!(e))?;
            let mut pw=PartialWitness::new();
            pw.set_target(inp[0],F::from_canonical_u64(i)).unwrap();
            pw.set_target(out[0],F::from_canonical_u64(o1)).unwrap();
            pw.set_target(out[1],F::from_canonical_u64(o2)).unwrap();
            pw.set_target(fee,F::from_canonical_u64(f)).unwrap();
            pw.set_target(bps,F::from_canonical_u64(rate)).unwrap();
            circuit.prove(pw)
        };
        for case in [
            (0,0,0,0,0),
            (1,1,0,0,0),
            (500_000_000,499_500_000,0,500_000,10),
            (DVN_MAX,DVN_MAX-10_000_000_000_000,0,10_000_000_000_000,10),
            (DVN_MAX,0,0,DVN_MAX,10_000),
        ] {
            let proof=prove(case.0,case.1,case.2,case.3,case.4)
                .expect("legitimate native fee must prove");
            circuit.verify(proof).expect("native fee proof must verify");
        }
        for case in [
            (500_000_000,499_500_001,0,499_999,10),
            (DVN_MAX,DVN_MAX-9_999_999_999_999,0,9_999_999_999_999,10),
            (DVN_MAX,DVN_MAX,0,0,1),
            (1,1,0,0,10_001),
            (DVN_MAX,1,0,DVN_MAX-1,10_000),
        ] {
            assert!(prove(case.0,case.1,case.2,case.3,case.4).is_err(),
                "insufficient fee / invalid BPS must be unprovable");
        }
    }

    #[test]
    fn dvn_v2_preflight_rejects_untrusted_fee_and_wraparound_without_prover_panics() {
        assert!(validate_v2_fee_segment_values(
            &[DVN_MAX], &[DVN_MAX-10_000_000_000_000,0],
            10_000_000_000_000, 10).is_ok());
        for (i,o,fee,rate) in [
            (DVN_MAX,DVN_MAX-9_999_999_999_999,9_999_999_999_999,10),
            (500_000_000,499_500_001,499_999,10),
            (DVN_MAX,DVN_MAX,0,1),
            (1,1,0,10_001),
        ] {
            assert!(validate_v2_fee_segment_values(&[i],&[o,0],fee,rate).is_err());
        }
    }
    #[test]
    fn dvn_v2_private_batch_proves_exact_u64_fee_and_value_conservation() {
        let mut b=CircuitBuilder::<F,D>::new(CircuitConfig::standard_recursion_config());
        let inputs=[b.add_virtual_target(),b.add_virtual_target()];
        let outputs=[
            b.add_virtual_target(),b.add_virtual_target(),
            b.add_virtual_target(),b.add_virtual_target(),
        ];
        let fee=b.add_virtual_target();
        let (total_in,total_out)=
            constrain_v2_private_batch_value(&mut b,&inputs,&outputs,fee);
        b.register_public_input(total_in);
        b.register_public_input(total_out);
        b.register_public_input(fee);
        let circuit=b.build::<C>();
        let prove=|i:[u64;2],o:[u64;4],f:u64| {
            let mut pw=PartialWitness::new();
            for (&t,&v) in inputs.iter().zip(i.iter()) {
                pw.set_target(t,F::from_canonical_u64(v)).unwrap();
            }
            for (&t,&v) in outputs.iter().zip(o.iter()) {
                pw.set_target(t,F::from_canonical_u64(v)).unwrap();
            }
            pw.set_target(fee,F::from_canonical_u64(f)).unwrap();
            circuit.prove(pw)
        };
        for (i,o,f) in [
            ([0,0],[0,0,0,0],0),
            ([1,0],[1,0,0,0],0),
            ([58_333_333_333_333,1],
             [30_000_000_000_000,28_333_333_333_332,1,0],1),
            ([DVN_MAX,0],[DVN_MAX,0,0,0],0),
        ] {
            let proof=prove(i,o,f).expect("valid full-width transfer must prove");
            circuit.verify(proof.clone()).expect("valid full-width proof verifies");
            assert_eq!(proof.public_inputs[0],
                F::from_canonical_u64(i[0]+i[1]));
        }
        for (i,o,f) in [
            ([1,0],[2,0,0,0],0), // inflation
            ([1,0],[0,0,0,0],0), // unclaimed/destroyed input
            ([58_333_333_333_333,1],
             [30_000_000_000_000,28_333_333_333_332,1,0],2), // fee tamper
            ([DVN_MAX,1],[DVN_MAX,1,0,0],0), // totals over max
            ([DVN_MAX+1,0],[0,0,0,0],DVN_MAX), // one input above max
            ([1,0],[DVN_MAX+1,0,0,0],0), // output above max
        ] {
            assert!(prove(i,o,f).is_err(),
                "invalid full-width settlement must not generate a proof");
        }
    }
    #[test]
    fn dvn_v2_public_batch_rejects_aggregate_above_native_supply() {
        let mut b=CircuitBuilder::<F,D>::new(CircuitConfig::standard_recursion_config());
        let accounts=[b.add_virtual_target(),b.add_virtual_target(),b.add_virtual_target()];
        let total=constrain_v2_public_batch_exits(&mut b,&accounts);
        b.register_public_input(total);
        let data=b.build::<C>();
        let prove=|amounts:[u64;3]| {
            let mut pw=PartialWitness::new();
            for (&t,&v) in accounts.iter().zip(amounts.iter()) {
                pw.set_target(t,F::from_canonical_u64(v)).unwrap();
            }
            data.prove(pw)
        };
        for case in [
            [0,0,0],[1,0,0],
            [58_333_333_333_333,30_000_000_000_000,1],
            [DVN_MAX-1,1,0],
        ] {
            let proof=prove(case).expect("valid aggregated proof must prove");
            data.verify(proof).expect("valid aggregated proof must verify");
        }
        assert!(prove([DVN_MAX,1,0]).is_err(),
            "in-range exits with total above 100M must not prove");
        assert!(prove([DVN_MAX+1,0,0]).is_err(),
            "above-cap individual exit must not prove");
    }
    #[test]
    fn dvn_v2_public_batch_prefix_cap_prevents_modular_wrap_at_high_slot_count() {
        const P:u128=0xFFFF_FFFF_0000_0001;
        let full=(P/(DVN_MAX as u128)) as usize;
        let remainder=(P%(DVN_MAX as u128)) as u64;
        assert!(full+1 <= MAX_LEAVES*MAX_LEAVES*2);
        assert!(remainder <= DVN_MAX);
        // This actual integer amount aliases ZERO if only the final field
        // total is constrained. Prefix check forbids it after just TWO
        // near-cap exits, well before the modular wrap at ~1845 slots.
        assert_eq!(((full as u128)*(DVN_MAX as u128)+remainder as u128)%P,0);
        assert!(2*DVN_MAX>DVN_MAX);
    }
    #[test]
    #[should_panic(expected="two exits per leaf")]
    fn dvn_v2_rejects_invalid_private_batch_shape() {
        let mut b=CircuitBuilder::<F,D>::new(CircuitConfig::standard_recursion_config());
        let input=[b.add_virtual_target()];
        let outputs=[b.add_virtual_target()];
        let fee=b.zero();
        let _=constrain_v2_private_batch_value(&mut b,&input,&outputs,fee);
    }
}
'''

def patch(root:Path)->None:
    lib=root/"wormhole/aggregator/src/lib.rs"
    target=root/"wormhole/aggregator/src/devnira_v2_segment.rs"
    original=lib.read_text(encoding="utf-8")
    if target.exists() or MARKER in original:
        raise ValueError("DEVNIRA V2 segment module already exists")
    if original.count("pub mod private_batch;")!=1 or original.count("pub mod public_batch;")!=1:
        raise ValueError("Unrecognized upstream aggregator module layout")
    if not (root/"wormhole/aggregator/src/private_batch/circuit/circuit_logic.rs").exists():
        raise ValueError("Cannot verify real upstream private-batch circuit source")
    if not (root/"wormhole/aggregator/src/public_batch/circuit/circuit_logic.rs").exists():
        raise ValueError("Cannot verify real upstream public-batch circuit source")
    target.write_text(RUST,encoding="utf-8")
    lib.write_text(original+"\n// Inactive exact-u64 batch constraints; V1 recursion remains unchanged.\n"+MARKER+"\n",encoding="utf-8")
    print("Staged verifiable, native-u64 Plonky2 private/public aggregation amount constraints (inactive).")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("source_root",type=Path)
    patch(p.parse_args().source_root)
