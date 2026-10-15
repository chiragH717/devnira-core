#!/usr/bin/env python3
"""Add an opt-in native-amount Merkle-root and chain-domain nullifier proof.

This is an ACTUAL Plonky2 test circuit, not active wormhole settlement. Its
fixed one-level 4-ary path is a test vector only; any live protocol also needs
full variable-depth proof, authorized spend key, private batches and persistent
root/nullifier state.
"""
from pathlib import Path
import argparse

MARKER="// DEVNIRA proof-side root/nullifier candidate tests (NOT ACTIVE)."
TEST= r'''
// DEVNIRA proof-side root/nullifier candidate tests (NOT ACTIVE).
#[cfg(test)]
mod devnira_v2_merkle_nullifier_tests {
    use super::{constrain_native_dvn_authenticated_spend, DVN_NATIVE_MAX};
    use plonky2::{
        field::types::Field,
        hash::{hash_types::{HashOut, HashOutTarget}, poseidon2::Poseidon2Hash},
        iop::{target::Target, witness::{PartialWitness,WitnessWrite}},
        plonk::{circuit_builder::CircuitBuilder, circuit_data::{CircuitConfig,CircuitData}, config::Hasher},
    };
    use zk_circuits_common::{
        circuit::{F,C,D},
        serialization::digest_to_bytes,
    };
    use core::array;

    /// Test-only domain tag: on-chain domain separation must commit the actual
    /// unique genesis hash, active verifier key, and future spec version.
    const DVN_NULLIFIER_V2_TEST_DOMAIN:u64=0x4456_4e5f_5a4b_5632;

    struct Targets {
        account:[Target;4],
        count:[Target;2],
        asset:Target,
        input:Target,
        out1:Target,
        out2:Target,
        fee:Target,
        siblings:[HashOutTarget;3],
        position:Target,
        root:HashOutTarget,
        chain_hash:HashOutTarget,
        nullifier:HashOutTarget,
    }
    fn build()->(CircuitData<F,C,D>,Targets) {
        let mut b=CircuitBuilder::<F,D>::new(CircuitConfig::standard_recursion_config());
        let account=array::from_fn(|_|b.add_virtual_target());
        let count=array::from_fn(|_|b.add_virtual_target());
        let asset=b.add_virtual_target();
        let input=b.add_virtual_target();
        let out1=b.add_virtual_target();
        let out2=b.add_virtual_target();
        let fee=b.add_virtual_target();
        let siblings=array::from_fn(|_|b.add_virtual_hash());
        let position=b.add_virtual_target();
        let root=b.add_virtual_hash();
        let chain_hash=b.add_virtual_hash();
        let nullifier=b.add_virtual_hash();
        let leaf=constrain_native_dvn_authenticated_spend(
            &mut b,account,count,asset,input,out1,out2,fee);

        // No dummy/unfunded leaf may pass this particular nonzero withdrawal
        // candidate. Do not pretend this provides sender ownership.
        let zero=b.zero();
        let zero_input=b.is_equal(input,zero);
        b.assert_zero(zero_input.target);
        // A client-chosen all-zero network tag is forbidden (NOT enough to
        // authenticate the network; runtime must pin exact real genesis).
        let mut zero_tag=b.one();
        for limb in &chain_hash.elements {
            let eq=b.is_equal(*limb,zero);
            zero_tag=b.mul(zero_tag,eq.target);
        }
        b.assert_zero(zero_tag);

        // Real upstream ZK tree uses 4-ary sorted children hashed from 16
        // compact Goldilocks felts. Position is a private witness selecting
        // the current leaf's location among three pre-sorted sibling hashes.
        b.range_check(position,2);
        let one=b.one();
        let two=b.constant(F::from_canonical_u64(2));
        let three=b.constant(F::from_canonical_u64(3));
        let pos0=b.is_equal(position,zero);
        let pos1=b.is_equal(position,one);
        let pos2=b.is_equal(position,two);
        let pos3=b.is_equal(position,three);
        let pos01=b.or(pos0,pos1);
        let children:[HashOutTarget;4]=array::from_fn(|slot|HashOutTarget{
            elements:array::from_fn(|limb| match slot {
                0=>b.select(pos0,leaf.elements[limb],siblings[0].elements[limb]),
                1=>{
                    let sib=b.select(pos0,siblings[0].elements[limb],siblings[1].elements[limb]);
                    b.select(pos1,leaf.elements[limb],sib)
                },
                2=>{
                    let sib=b.select(pos01,siblings[1].elements[limb],siblings[2].elements[limb]);
                    b.select(pos2,leaf.elements[limb],sib)
                },
                3=>b.select(pos3,leaf.elements[limb],siblings[2].elements[limb]),
                _=>unreachable!(),
            }),
        });
        let mut preimage=alloc::vec::Vec::with_capacity(16);
        for child in &children {
            preimage.extend_from_slice(&child.elements);
        }
        let calculated_root=b.poseidon2_hash_no_pad(preimage);
        for (got,expected) in calculated_root.elements.iter().zip(root.elements.iter()){
            b.connect(*got,*expected);
        }

        // The commitment is domain separated with the chain hash. This
        // deterministic public tag can serve as a future nullifier ONLY when
        // checked against on-chain UsedNullifiers at settlement.
        let domain=b.constant(F::from_canonical_u64(DVN_NULLIFIER_V2_TEST_DOMAIN));
        let mut npi=alloc::vec::Vec::with_capacity(9);
        npi.push(domain);
        npi.extend_from_slice(&leaf.elements);
        npi.extend_from_slice(&chain_hash.elements);
        let calculated_nullifier=b.poseidon2_hash_no_pad(npi);
        for (got,expected) in calculated_nullifier.elements.iter().zip(nullifier.elements.iter()){
            b.connect(*got,*expected);
        }

        // Root, network identity and nullifier must be PUBLIC to the verifier
        // and bound to outputs and fees. These are 15 canonical public felts.
        b.register_public_inputs(&root.elements);
        b.register_public_inputs(&chain_hash.elements);
        b.register_public_inputs(&nullifier.elements);
        b.register_public_input(out1);
        b.register_public_input(out2);
        b.register_public_input(fee);
        let data=b.build::<C>();
        assert_eq!(data.common.num_public_inputs,15);
        (data,Targets{account,count,asset,input,out1,out2,fee,siblings,position,root,chain_hash,nullifier})
    }
    fn f(v:u64)->F {F::from_canonical_u64(v)}
    fn example_fixture() ->(HashOut<F>,[HashOut<F>;3],u64,HashOut<F>,HashOut<F>) {
        let leaf=Poseidon2Hash::hash_no_pad(&[
            f(100),f(101),f(102),f(103),f(0),f(1),f(0),f(500_000_000),
        ]);
        let mut children=[
            leaf,
            Poseidon2Hash::hash_no_pad(&[f(90)]),
            Poseidon2Hash::hash_no_pad(&[f(91)]),
            Poseidon2Hash::hash_no_pad(&[f(92)]),
        ];
        // Runtime sorts byte hashes, NOT field values.
        children.sort_by_key(|hash|digest_to_bytes(&hash.elements));
        let position=children.iter().position(|h| *h==leaf).unwrap();
        let mut siblings=alloc::vec::Vec::new();
        for (i,h) in children.iter().enumerate(){
            if i!=position {siblings.push(*h);}
        }
        let preimage:alloc::vec::Vec<F>=children.iter()
            .flat_map(|h|h.elements.iter().copied()).collect();
        let root=Poseidon2Hash::hash_no_pad(&preimage);
        let chain_hash=HashOut{elements:[f(11),f(12),f(13),f(14)]};
        let mut npi=alloc::vec![f(DVN_NULLIFIER_V2_TEST_DOMAIN)];
        npi.extend_from_slice(&leaf.elements);
        npi.extend_from_slice(&chain_hash.elements);
        let nullifier=Poseidon2Hash::hash_no_pad(&npi);
        (root,siblings.try_into().unwrap(),position as u64,chain_hash,nullifier)
    }
    fn fill(t:&Targets)->PartialWitness<F>{
        let (root,siblings,position,chain_hash,nullifier)=example_fixture();
        let mut pw=PartialWitness::new();
        for (idx,target) in t.account.iter().enumerate(){
            pw.set_target(*target,f(100+idx as u64)).unwrap();
        }
        pw.set_target(t.count[0],f(0)).unwrap();
        pw.set_target(t.count[1],f(1)).unwrap();
        pw.set_target(t.asset,f(0)).unwrap();
        pw.set_target(t.input,f(500_000_000)).unwrap();
        pw.set_target(t.out1,f(300_000_001)).unwrap();
        pw.set_target(t.out2,f(199_999_998)).unwrap();
        pw.set_target(t.fee,f(1)).unwrap();
        pw.set_target(t.position,f(position)).unwrap();
        for (i,sibling) in siblings.iter().enumerate(){
            pw.set_hash_target(t.siblings[i],*sibling).unwrap();
        }
        pw.set_hash_target(t.root,root).unwrap();
        pw.set_hash_target(t.chain_hash,chain_hash).unwrap();
        pw.set_hash_target(t.nullifier,nullifier).unwrap();
        pw
    }
    #[test]
    fn dvn_v2_merkle_real_native_root_and_nullifier_proof() {
        let (data,t)=build();
        let proof=data.prove(fill(&t)).expect("valid 4ary native leaf Merkle path must prove");
        data.verify(proof.clone()).expect("valid path should verify");
        assert_eq!(proof.public_inputs.len(),15);
        assert_eq!(proof.public_inputs[12],f(300_000_001));
        assert_eq!(proof.public_inputs[13],f(199_999_998));
        assert_eq!(proof.public_inputs[14],f(1));
        let mut mutated=proof;
        mutated.public_inputs[0]=f(99);
        assert!(data.verify(mutated).is_err(),"root tamper invalidates verified proof");
    }

    #[test]
    fn dvn_v2_merkle_rejects_forged_root_sibling_and_nullifier() {
        use std::panic::{catch_unwind,AssertUnwindSafe};
        let (data,t)=build();
        let mut wrong_root=fill(&t);
        wrong_root.set_hash_target(t.root,HashOut{elements:[f(9),f(8),f(7),f(6)]}).unwrap();
        let out=catch_unwind(AssertUnwindSafe(||data.prove(wrong_root)));
        assert!(out.is_err()||out.unwrap().is_err(),"forged Merkle root proved");
        let mut wrong_sibling=fill(&t);
        wrong_sibling.set_hash_target(t.siblings[0],HashOut{elements:[f(5);4]}).unwrap();
        let out=catch_unwind(AssertUnwindSafe(||data.prove(wrong_sibling)));
        assert!(out.is_err()||out.unwrap().is_err(),"forged sibling proved");
        let mut wrong_nullifier=fill(&t);
        wrong_nullifier.set_hash_target(t.nullifier,HashOut{elements:[f(4);4]}).unwrap();
        let out=catch_unwind(AssertUnwindSafe(||data.prove(wrong_nullifier)));
        assert!(out.is_err()||out.unwrap().is_err(),"forged nullifier proved");
    }

    #[test]
    fn dvn_v2_merkle_rejects_foreign_network_zero_and_reused_nullifier() {
        use std::panic::{catch_unwind,AssertUnwindSafe};
        let (data,t)=build();
        let mut changed_network=fill(&t);
        changed_network.set_hash_target(t.chain_hash,HashOut{elements:[f(15);4]}).unwrap();
        let out=catch_unwind(AssertUnwindSafe(||data.prove(changed_network)));
        assert!(out.is_err()||out.unwrap().is_err(),
            "old nullifier must not authenticate under different network tag");
        let mut zero_network=fill(&t);
        zero_network.set_hash_target(t.chain_hash,HashOut{elements:[f(0);4]}).unwrap();
        let out=catch_unwind(AssertUnwindSafe(||data.prove(zero_network)));
        assert!(out.is_err()||out.unwrap().is_err(),"zero-genesis network must fail");
        let mut attempted_inflation=fill(&t);
        attempted_inflation.set_target(t.out1,f(300_000_002)).unwrap();
        let out=catch_unwind(AssertUnwindSafe(||data.prove(attempted_inflation)));
        assert!(out.is_err()||out.unwrap().is_err(),"unauthorized extra DVN unit must fail");
    }

    #[test]
    fn dvn_v2_merkle_amount_max_is_native_eight_decimal_units() {
        // A circuit test cannot prove that a proof's PUBLIC root is actually
        // the chain's finalized, accepted historical root. Runtime must check.
        assert_eq!(DVN_NATIVE_MAX,100_000_000*100_000_000);
    }
}
''';

def patch(root: Path) -> None:
    file=root/"wormhole/circuit/src/devnira_v2_amount_circuit.rs"
    source=file.read_text(encoding="utf-8")
    if MARKER in source:
        raise ValueError("V2 Merkle nullifier candidate already installed")
    if "pub fn constrain_native_dvn_authenticated_spend" not in source:
        raise ValueError("STOP: native authenticated spend circuit must be inserted first")
    if "pub fn constrain_native_dvn_value_conservation" not in source:
        raise ValueError("STOP: native amount conservation must be constrained first")
    if "pub const DVN_NATIVE_MAX:" not in source:
        raise ValueError("STOP: canonical 8-decimal DVN cap source missing")
    file.write_text(source+"\\n"+TEST,encoding="utf-8")
    print("Staged cryptographic one-level 4ary V2 Merkle + chain-domain nullifier candidate; NOT live.")

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("pinned_zk_circuits_source",type=Path)
    patch(p.parse_args().pinned_zk_circuits_source)
