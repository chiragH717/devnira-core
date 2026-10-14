#!/usr/bin/env python3
"""Add a REAL opt-in V2 recursive leaf -> aggregator proof integration test.

This uses the pinned Plonky2 crate, fixed inner verifier key, exact eight-
decimal amount commitments and a real recursively verified outer proof.
It does NOT activate the existing V1 mainnet proof verifier.
"""
from pathlib import Path
import argparse

MODULE_NAME="devnira_v2_recursive_candidate"
MARKER=f"pub mod {MODULE_NAME};"
RUST=r'''//! DEVNIRA V2 opt-in cryptographically verified leaf -> recursive wrapper.
//!
//! The verified inner proof commits the exact 8-decimal native amount to
//! Poseidon2 and enforces input == output1 + output2 + fee.
//! The outer circuit has a FIXED inner verifier key, exposes all inner public
//! inputs and range-checks the aggregate of the two outputs as native u64.
//!
//! WARNING: this is a two-layer *candidate* proof, NOT the active V1
//! private/public batching engine, withdrawal verifier or native chain runtime.
use anyhow::{ensure, Result};
use plonky2::{
    plonk::{
        circuit_builder::CircuitBuilder,
        circuit_data::{CircuitConfig, CircuitData},
        proof::ProofWithPublicInputsTarget,
    },
};
use zk_circuits_common::circuit::{F,C,D};
use crate::common::recursive::add_recursive_verifiers;
use crate::devnira_v2_segment::{
    constrain_v2_native_amount, constrain_v2_public_batch_exits, MAX_LEAVES,
};

/// The seven real V2 inner public inputs are:
/// [poseidon2_leaf_hash_4, output1_native_u64, output2_native_u64, fee_native_u64].
/// The original *input* amount remains a private witness, committed into
/// the Poseidon2 leaf hash. Root membership and actual nullifiers remain
/// separate missing obligations.
pub const V2_LEAF_PUBLIC_INPUT_LEN:usize=7;

pub fn build_v2_leaf_recursive_wrapper(
    inner: &CircuitData<F,C,D>,
)->Result<CircuitData<F,C,D>> {
    ensure!(inner.common.num_public_inputs==V2_LEAF_PUBLIC_INPUT_LEN,
        "STOP: unexpected V2 leaf public input count");
    let mut builder=CircuitBuilder::<F,D>::new(CircuitConfig::standard_recursion_config());
    // Constant verifier key: a witness cannot substitute a permissive
    // malicious circuit with the same public input count.
    let proofs=add_recursive_verifiers::<F,C,D>(
        &mut builder,&inner.common,&inner.verifier_only,1,
    )?;
    let pis=&proofs[0].public_inputs;
    constrain_v2_public_batch_exits(&mut builder,&pis[4..6]);
    builder.register_public_inputs(pis);
    Ok(builder.build::<C>())
}

/// Development-only fixed-key recursive aggregation of 2..=64 genuine V2
/// Poseidon2 leaf proofs. This is NOT Quantus's production private-batch tree.
/// Every leaf's exact hash, payouts, and fee remain public inputs; the two
/// final public inputs bind the combined native payouts and fees.
///
/// Public layout: [leaf0 7 PIs, ..., leafN 7 PIs, total_payout, total_fee].
/// Verifying leaf conservation alone does not prevent replay or prove tree
/// membership. Runtime nullifiers, roots and chain-specific domain separation
/// must be integrated and reviewed before activating withdrawals.
pub fn build_v2_multi_leaf_recursive_batch(
    inner: &CircuitData<F,C,D>,
    num_leaves: usize,
)->Result<(CircuitData<F,C,D>,Vec<ProofWithPublicInputsTarget<D>>)> {
    ensure!(inner.common.num_public_inputs==V2_LEAF_PUBLIC_INPUT_LEN,
        "STOP: mismatched V2 Poseidon2 leaf PI schema");
    ensure!((2..=MAX_LEAVES).contains(&num_leaves),
        "STOP: batch leaf count must be between 2 and 64");
    let mut builder=CircuitBuilder::<F,D>::new(CircuitConfig::standard_recursion_config());
    // Every proof uses the SAME constant, non-witness verifier key.
    let proofs=add_recursive_verifiers::<F,C,D>(
        &mut builder,&inner.common,&inner.verifier_only,num_leaves,
    )?;
    let mut outputs=Vec::with_capacity(num_leaves*2);
    let mut total_fee=builder.zero();
    for proof in &proofs {
        builder.register_public_inputs(&proof.public_inputs);
        outputs.extend_from_slice(&proof.public_inputs[4..6]);
        total_fee=builder.add(total_fee,proof.public_inputs[6]);
        // Bound EVERY fee prefix; no arithmetic in Goldilocks can wrap.
        constrain_v2_native_amount(&mut builder,total_fee);
    }
    let total_payout=constrain_v2_public_batch_exits(&mut builder,&outputs);
    let total_spent=builder.add(total_payout,total_fee);
    constrain_v2_native_amount(&mut builder,total_spent);
    builder.register_public_input(total_payout);
    builder.register_public_input(total_fee);
    Ok((builder.build::<C>(),proofs))
}

#[cfg(test)]
mod tests {
    use super::*;
    use plonky2::{
        field::types::Field,
        iop::{target::Target,witness::{PartialWitness,WitnessWrite}},
    };
    use wormhole_circuit::devnira_v2_amount_circuit::constrain_native_dvn_authenticated_spend;
    use crate::devnira_v2_segment::DVN_MAX;

    struct LeafFixture {
        leaf: CircuitData<F,C,D>,
        address:[Target;4],
        count:[Target;2],
        asset:Target,
        amount:Target,
        output1:Target,
        output2:Target,
        fee:Target,
    }
    fn leaf_fixture()->LeafFixture{
        let mut builder=CircuitBuilder::<F,D>::new(CircuitConfig::standard_recursion_config());
        let address=core::array::from_fn(|_|builder.add_virtual_target());
        let count=core::array::from_fn(|_|builder.add_virtual_target());
        let asset=builder.add_virtual_target();
        let amount=builder.add_virtual_target();
        let output1=builder.add_virtual_target();
        let output2=builder.add_virtual_target();
        let fee=builder.add_virtual_target();
        let leaf_hash=constrain_native_dvn_authenticated_spend(
            &mut builder,address,count,asset,amount,output1,output2,fee,
        );
        builder.register_public_inputs(&leaf_hash.elements);
        builder.register_public_input(output1);
        builder.register_public_input(output2);
        builder.register_public_input(fee);
        let leaf=builder.build::<C>();
        assert_eq!(leaf.common.num_public_inputs,V2_LEAF_PUBLIC_INPUT_LEN);
        LeafFixture{leaf,address,count,asset,amount,output1,output2,fee}
    }
    fn prove_leaf(
        f:&LeafFixture,amount:u64,out1:u64,out2:u64,fee:u64
    )->anyhow::Result<plonky2::plonk::proof::ProofWithPublicInputs<F,C,D>>{
        let mut pw=PartialWitness::new();
        for (i,target) in f.address.iter().enumerate(){
            pw.set_target(*target,F::from_canonical_u64(100+i as u64))?;
        }
        pw.set_target(f.count[0],F::ZERO)?;
        pw.set_target(f.count[1],F::ONE)?;
        pw.set_target(f.asset,F::ZERO)?;
        pw.set_target(f.amount,F::from_canonical_u64(amount))?;
        pw.set_target(f.output1,F::from_canonical_u64(out1))?;
        pw.set_target(f.output2,F::from_canonical_u64(out2))?;
        pw.set_target(f.fee,F::from_canonical_u64(fee))?;
        f.leaf.prove(pw)
    }

    /// Actual native witness -> Poseidon2 leaf proof -> recursive proof ->
    /// verified outer public outputs. All cryptographic checks are from the
    /// pinned Plonky2 library, not a string/source inspection.
    #[test]
    fn dvn_v2_actual_recursive_poseidon2_leaf_proves_and_verifies() {
        let f=leaf_fixture();
        let outer=build_v2_leaf_recursive_wrapper(&f.leaf).unwrap();
        let valid=prove_leaf(&f,500_000_000,300_000_001,199_999_998,1)
            .expect("valid full-precision 5 DVN leaf");
        f.leaf.verify(valid.clone()).expect("inner proof must verify");
        let mut pw=PartialWitness::new();
        let mut builder=CircuitBuilder::<F,D>::new(CircuitConfig::standard_recursion_config());
        // Reconstruct the IDENTICAL constant-key wrapper to derive targets.
        let targets=add_recursive_verifiers::<F,C,D>(
            &mut builder,&f.leaf.common,&f.leaf.verifier_only,1,
        ).unwrap();
        constrain_v2_public_batch_exits(&mut builder,&targets[0].public_inputs[4..6]);
        builder.register_public_inputs(&targets[0].public_inputs);
        let outer_for_witness=builder.build::<C>();
        pw.set_proof_with_pis_target(&targets[0],&valid).unwrap();
        let aggregate=outer_for_witness.prove(pw).expect("real V2 recursive proof");
        outer_for_witness.verify(aggregate.clone())
            .expect("real V2 recursive verify");
        assert_eq!(aggregate.public_inputs.len(),7);
        assert_eq!(aggregate.public_inputs[4],F::from_canonical_u64(300_000_001));
        assert_eq!(aggregate.public_inputs[5],F::from_canonical_u64(199_999_998));
        assert_eq!(aggregate.public_inputs[6],F::ONE);

        // The outer verifier hash is deterministic for the same inner VK,
        // constraints and public input layout.
        assert_eq!(outer.verifier_only.circuit_digest,
                   outer_for_witness.verifier_only.circuit_digest);

        let mut tampered=aggregate.clone();
        tampered.public_inputs[4]=F::from_canonical_u64(300_000_002);
        assert!(outer_for_witness.verify(tampered).is_err(),
            "cannot alter payout after proof verification");
        let mut tampered_fee=aggregate;
        tampered_fee.public_inputs[6]=F::from_canonical_u64(2);
        assert!(outer_for_witness.verify(tampered_fee).is_err(),
            "cannot alter fee after proof verification");

        // Export PUBLIC verifier artifacts for offline hash/circuit audit.
        // Never export private witnesses, signing keys or a prover binary.
        // These are development circuit artifacts, not active mainnet pins.
        if let Ok(output_dir)=std::env::var("DEVNIRA_TEST_ARTIFACT_DIR") {
            use plonky2::util::serialization::DefaultGateSerializer;
            let target=std::path::PathBuf::from(output_dir);
            std::fs::create_dir_all(&target).expect("artifact directory");
            let serializer=DefaultGateSerializer;
            std::fs::write(
                target.join("v2-leaf-verifier.bin"),
                f.leaf.verifier_only.to_bytes().expect("serialize leaf verifier"),
            ).expect("write leaf verifier");
            std::fs::write(
                target.join("v2-leaf-common.bin"),
                f.leaf.common.to_bytes(&serializer).expect("serialize leaf common"),
            ).expect("write leaf common");
            std::fs::write(
                target.join("v2-recursive-verifier.bin"),
                outer_for_witness.verifier_only.to_bytes()
                    .expect("serialize recursive verifier"),
            ).expect("write recursive verifier");
            std::fs::write(
                target.join("v2-recursive-common.bin"),
                outer_for_witness.common.to_bytes(&serializer)
                    .expect("serialize recursive common"),
            ).expect("write recursive common");
        }

        // The private witness is genuinely value conserving and capped.
        assert!(prove_leaf(&f,500_000_000,300_000_002,199_999_998,1).is_err(),
            "newly minted base unit cannot prove");
        assert!(prove_leaf(&f,DVN_MAX+1,0,0,0).is_err(),
            "exceeds 100M DVN maximum");
    }

    /// Two actual 8-decimal leaf proofs are verified by a constant-key
    /// recursive batch. Per-leaf conservation, total payouts, total fees and
    /// the 100M cap are constraints, not untrusted off-chain arithmetic.
    #[test]
    fn dvn_v2_batch_real_two_leaf_recursive_proof_enforces_exact_supply() {
        use std::panic::{catch_unwind,AssertUnwindSafe};
        let f=leaf_fixture();
        let (batch,targets)=build_v2_multi_leaf_recursive_batch(&f.leaf,2)
            .expect("valid two-leaf V2 batch");
        let first=prove_leaf(&f,500_000_000,300_000_001,199_999_998,1)
            .expect("first exact native leaf");
        let second=prove_leaf(&f,600_000_000,400_000_001,199_999_998,1)
            .expect("second exact native leaf");
        let mut pw=PartialWitness::new();
        pw.set_proof_with_pis_target(&targets[0],&first).unwrap();
        pw.set_proof_with_pis_target(&targets[1],&second).unwrap();
        let proof=batch.prove(pw).expect("valid two-leaf recursive proof");
        batch.verify(proof.clone()).expect("batch verifier must accept");
        assert_eq!(proof.public_inputs.len(),2*V2_LEAF_PUBLIC_INPUT_LEN+2);
        assert_eq!(proof.public_inputs[14],F::from_canonical_u64(1_099_999_998));
        assert_eq!(proof.public_inputs[15],F::from_canonical_u64(2));
        let mut changed_payout=proof.clone();
        changed_payout.public_inputs[14]=F::from_canonical_u64(1_099_999_999);
        assert!(batch.verify(changed_payout).is_err(),
            "altered batch payout must fail recursive verification");
        let mut changed_fee=proof;
        changed_fee.public_inputs[15]=F::from_canonical_u64(3);
        assert!(batch.verify(changed_fee).is_err(),
            "altered batch fee must fail recursive verification");

        // Both separate leaf proofs are individually valid, but their
        // sum breaches 100M by exactly one 8-decimal base unit.
        let max_leaf=prove_leaf(&f,DVN_MAX,DVN_MAX,0,0).unwrap();
        let one_leaf=prove_leaf(&f,1,1,0,0).unwrap();
        let mut overcap=PartialWitness::new();
        overcap.set_proof_with_pis_target(&targets[0],&max_leaf).unwrap();
        overcap.set_proof_with_pis_target(&targets[1],&one_leaf).unwrap();
        let rejected=catch_unwind(AssertUnwindSafe(||batch.prove(overcap)));
        assert!(rejected.is_err()||rejected.unwrap().is_err(),
            "two valid leaves must not inflate batch payout past DVN cap");
    }

    #[test]
    fn dvn_v2_batch_rejects_zero_one_or_oversized_leaf_count() {
        let f=leaf_fixture();
        for count in [0,1,MAX_LEAVES+1] {
            assert!(build_v2_multi_leaf_recursive_batch(&f.leaf,count).is_err());
        }
    }

    /// A malicious circuit may claim exactly the same seven PI positions,
    /// but carry no native DVN amount conservation or Poseidon constraints.
    /// Its self-valid proof MUST NOT be accepted by the fixed-key wrapper.
    #[test]
    fn dvn_v2_actual_recursive_rejects_foreign_key_with_identical_public_input_count() {
        use std::panic::{catch_unwind,AssertUnwindSafe};
        let f=leaf_fixture();
        let mut outer_builder=CircuitBuilder::<F,D>::new(CircuitConfig::standard_recursion_config());
        let targets=add_recursive_verifiers::<F,C,D>(
            &mut outer_builder,&f.leaf.common,&f.leaf.verifier_only,1,
        ).unwrap();
        constrain_v2_public_batch_exits(
            &mut outer_builder,&targets[0].public_inputs[4..6],
        );
        outer_builder.register_public_inputs(&targets[0].public_inputs);
        let wrapper=outer_builder.build::<C>();

        let mut attacker=CircuitBuilder::<F,D>::new(CircuitConfig::standard_recursion_config());
        let bogus_pis:Vec<Target>=(0..V2_LEAF_PUBLIC_INPUT_LEN)
            .map(|_|attacker.add_virtual_public_input()).collect();
        let attacker_circuit=attacker.build::<C>();
        let mut attacker_witness=PartialWitness::new();
        for (idx,target) in bogus_pis.iter().enumerate(){
            let val=if idx==4 {DVN_MAX} else if idx==5 {1} else {0};
            attacker_witness.set_target(*target,F::from_canonical_u64(val)).unwrap();
        }
        let bogus=attacker_circuit.prove(attacker_witness)
            .expect("attacker's unconstrained circuit proves trivially");
        assert_eq!(bogus.public_inputs.len(),V2_LEAF_PUBLIC_INPUT_LEN);
        // Attempt to substitute bogus proof into wrapper that pins a
        // DIFFERENT real Poseidon-constrained inner verifier key.
        let rejected=catch_unwind(AssertUnwindSafe(||{
            let mut witness=PartialWitness::new();
            witness.set_proof_with_pis_target(&targets[0],&bogus).unwrap();
            wrapper.prove(witness)
        }));
        assert!(
            rejected.is_err()||rejected.unwrap().is_err(),
            "FOREIGN VERIFIER KEY SUBSTITUTION ACCEPTED"
        );
    }

    #[test]
    fn dvn_v2_recursive_refuses_wrong_inner_public_input_layout() {
        let mut builder=CircuitBuilder::<F,D>::new(CircuitConfig::standard_recursion_config());
        let t=builder.add_virtual_target();
        builder.register_public_input(t);
        let not_a_leaf=builder.build::<C>();
        assert!(build_v2_leaf_recursive_wrapper(&not_a_leaf).is_err());
    }
}
'''

def patch(root:Path):
    base=root/"wormhole/aggregator/src"
    lib=base/"lib.rs"
    mod=base/(MODULE_NAME+".rs")
    source=lib.read_text(encoding="utf-8")
    if mod.exists() or MARKER in source:
        raise ValueError("STOP: V2 recursive proof candidate already installed")
    for evidence in (
        "pub mod common;","pub mod private_batch;","pub mod public_batch;",
        "pub mod devnira_v2_segment;",
    ):
        if evidence not in source:
            raise ValueError("STOP: pinned source missing V2 aggregation dependency: "+evidence)
    leaf=root/"wormhole/circuit/src/devnira_v2_amount_circuit.rs"
    if not leaf.is_file() or "constrain_native_dvn_authenticated_spend" not in leaf.read_text():
        raise ValueError("STOP: actual V2 Poseidon2 leaf+conservation proof must be staged first")
    mod.write_text(RUST,encoding="utf-8")
    lib.write_text(source+"\n// Opt-in source-test only; production proof path remains V1.\n"+MARKER+"\n",encoding="utf-8")
    print("Staged REAL Plonky2 V2 recursive leaf proof with constant verifier key (NOT active chain).")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("upstream_source",type=Path)
    patch(ap.parse_args().upstream_source)
