#!/usr/bin/env python3
"""Add ACTUAL Plonky2 bounded-depth DEVNIRA V2 Merkle proof regression suite.

The existing one-level prototype proved 4-ary membership only for exactly one
parent. This extension uses a private depth and multiple sorted 4-ary levels,
enforcing root equality and native DVN conservation while binding nullifier
to a publicly provided network tag. It remains INACTIVE in chain settlement.
"""
import argparse
from pathlib import Path

MARKER="// DEVNIRA V2 VARIABLE-DEPTH 4-ARY ROOT CANDIDATE — NOT ACTIVE ON-CHAIN."
RUST=r'''
// DEVNIRA V2 VARIABLE-DEPTH 4-ARY ROOT CANDIDATE — NOT ACTIVE ON-CHAIN.
#[cfg(test)]
mod devnira_v2_full_merkle_tests {
    use super::{constrain_native_dvn_authenticated_spend,DVN_NATIVE_MAX};
    use alloc::vec::Vec;
    use core::array;
    use plonky2::{
        field::types::Field,
        hash::{hash_types::{HashOut, HashOutTarget}, poseidon2::Poseidon2Hash},
        iop::{target::Target,witness::{PartialWitness,WitnessWrite}},
        plonk::{circuit_builder::CircuitBuilder, circuit_data::{CircuitConfig,CircuitData},config::Hasher},
    };
    use zk_circuits_common::{
        circuit::{F,C,D},
        gadget_builder::GadgetBuilder,
        gadgets::{enforce_target_less_than_const,is_const_less_than},
        serialization::digest_to_bytes,
        zk_merkle::MAX_DEPTH,
    };
    const NULLIFIER_DOMAIN:u64=0x4456_4e5f_5a4b_5632;
    // The hash is only chain-tag-bound. Production settlement MUST check
    // the exact independent genesis and key ownership; public chain tag
    // alone does not provide global chain authentication.
    struct WitnessTargets {
        account:[Target;4],count:[Target;2],asset:Target,amount:Target,
        out1:Target,out2:Target,fee:Target,depth:Target,
        siblings:Vec<[HashOutTarget;3]>,positions:Vec<Target>,
        root:HashOutTarget,chain:HashOutTarget,nullifier:HashOutTarget,
    }
    fn circuit(layers:usize)->(CircuitData<F,C,D>,WitnessTargets) {
        assert!((1..=MAX_DEPTH).contains(&layers),"actual ZK-tree depth cap");
        let mut b=CircuitBuilder::<F,D>::new(CircuitConfig::standard_recursion_config());
        let account=array::from_fn(|_|b.add_virtual_target());
        let count=array::from_fn(|_|b.add_virtual_target());
        let asset=b.add_virtual_target();
        let amount=b.add_virtual_target();
        let out1=b.add_virtual_target();
        let out2=b.add_virtual_target();
        let fee=b.add_virtual_target();
        let leaf=constrain_native_dvn_authenticated_spend(
            &mut b,account,count,asset,amount,out1,out2,fee);
        let depth=b.add_virtual_target();
        let zero=b.zero();
        let nonzero_amount=b.is_equal(amount,zero);
        b.assert_zero(nonzero_amount.target);
        let nonzero_depth=b.is_equal(depth,zero);
        b.assert_zero(nonzero_depth.target);
        let bits=(usize::BITS - layers.leading_zeros()) as usize;
        enforce_target_less_than_const(&mut b,depth,layers+1,bits);
        let mut positions=Vec::new();
        let mut siblings=Vec::new();
        let mut current=leaf;
        for level in 0..layers {
            let active=is_const_less_than(&mut b,level,depth,bits);
            let position=b.add_virtual_target();
            b.range_check(position,2);
            let three_siblings=array::from_fn(|_|b.add_virtual_hash());
            let one=b.one();
            let two=b.constant(F::from_canonical_u64(2));
            let three=b.constant(F::from_canonical_u64(3));
            let p0=b.is_equal(position,zero);
            let p1=b.is_equal(position,one);
            let p2=b.is_equal(position,two);
            let p3=b.is_equal(position,three);
            let p01=b.or(p0,p1);
            let children:[HashOutTarget;4]=array::from_fn(|slot|HashOutTarget{
                elements:array::from_fn(|limb|match slot{
                    0=>b.select(p0,current.elements[limb],three_siblings[0].elements[limb]),
                    1=>{
                        let sib=b.select(p0,three_siblings[0].elements[limb],
                                          three_siblings[1].elements[limb]);
                        b.select(p1,current.elements[limb],sib)
                    },
                    2=>{
                        let sib=b.select(p01,three_siblings[1].elements[limb],
                                          three_siblings[2].elements[limb]);
                        b.select(p2,current.elements[limb],sib)
                    },
                    3=>b.select(p3,current.elements[limb],three_siblings[2].elements[limb]),
                    _=>unreachable!(),
                }),
            });
            let mut preimage=Vec::with_capacity(16);
            for child in &children {preimage.extend_from_slice(&child.elements);}
            let parent=b.poseidon2_hash_no_pad(preimage);
            current=HashOutTarget {elements:array::from_fn(|i|
                b.select(active,parent.elements[i],current.elements[i]))};
            positions.push(position);
            siblings.push(three_siblings);
        }
        let root=b.add_virtual_hash();
        for i in 0..4{b.connect(current.elements[i],root.elements[i]);}
        let chain=b.add_virtual_hash();
        let mut zero_chain=b.one();
        for limb in &chain.elements {
            let eq=b.is_equal(*limb,zero);
            zero_chain=b.mul(zero_chain,eq.target);
        }
        b.assert_zero(zero_chain);
        let nullifier=b.add_virtual_hash();
        let mut npi=Vec::with_capacity(9);
        npi.push(b.constant(F::from_canonical_u64(NULLIFIER_DOMAIN)));
        npi.extend_from_slice(&leaf.elements);
        npi.extend_from_slice(&chain.elements);
        let calculated=b.poseidon2_hash_no_pad(npi);
        for i in 0..4{b.connect(calculated.elements[i],nullifier.elements[i]);}
        b.register_public_inputs(&root.elements);
        b.register_public_inputs(&chain.elements);
        b.register_public_inputs(&nullifier.elements);
        b.register_public_input(out1);
        b.register_public_input(out2);
        b.register_public_input(fee);
        let data=b.build::<C>();
        assert_eq!(data.common.num_public_inputs,15);
        (data,WitnessTargets{account,count,asset,amount,out1,out2,fee,
            depth,siblings,positions,root,chain,nullifier})
    }
    fn f(value:u64)->F{F::from_canonical_u64(value)}
    fn hash(words:&[u64])->HashOut<F>{
        let values:Vec<F>=words.iter().copied().map(f).collect();
        Poseidon2Hash::hash_no_pad(&values)
    }
    fn native_leaf()->HashOut<F>{
        hash(&[100,101,102,103,0,1,0,500_000_000])
    }
    fn path(depth:usize)->(HashOut<F>,Vec<[HashOut<F>;3]>,Vec<u8>){
        let mut current=native_leaf();
        let mut all_siblings=Vec::new();
        let mut all_positions=Vec::new();
        for level in 0..depth{
            let seed=1000+level as u64*10;
            let mut children=[current,hash(&[seed]),hash(&[seed+1]),hash(&[seed+2])];
            // Quantus pallet-zk-tree SORTS 32-byte serialized digests, not
            // the field-element tuple order, before compact-node hashing.
            children.sort_by_key(|child|digest_to_bytes(&child.elements));
            let index=children.iter().position(|h|*h==current).unwrap();
            all_positions.push(index as u8);
            let rest:Vec<_>=children.iter().enumerate().filter_map(
                |(i,h)|if i==index{None}else{Some(*h)}).collect();
            all_siblings.push(rest.try_into().unwrap());
            let preimage:Vec<F>=children.iter().flat_map(
                |h|h.elements.iter().copied()).collect();
            current=Poseidon2Hash::hash_no_pad(&preimage);
        }
        (current,all_siblings,all_positions)
    }
    fn fill(t:&WitnessTargets,actual_depth:usize,fault:&str)->PartialWitness<F>{
        let (root,proof_siblings,proof_positions)=path(actual_depth);
        let chain=HashOut{elements:[f(11),f(12),f(13),f(14)]};
        let mut npi=vec![f(NULLIFIER_DOMAIN)];
        npi.extend_from_slice(&native_leaf().elements);
        npi.extend_from_slice(&chain.elements);
        let nullifier=Poseidon2Hash::hash_no_pad(&npi);
        let mut w=PartialWitness::new();
        for (i,target) in t.account.iter().enumerate(){
            w.set_target(*target,f(100+i as u64)).unwrap();
        }
        w.set_target(t.count[0],f(0)).unwrap();
        w.set_target(t.count[1],f(1)).unwrap();
        w.set_target(t.asset,f(0)).unwrap();
        w.set_target(t.amount,f(500_000_000)).unwrap();
        w.set_target(t.out1,f(if fault=="inflation"{300_000_002}else{300_000_001})).unwrap();
        w.set_target(t.out2,f(199_999_998)).unwrap();
        w.set_target(t.fee,f(1)).unwrap();
        w.set_target(t.depth,f(if fault=="zero_depth"{0}else{actual_depth as u64})).unwrap();
        let zero_hash=HashOut{elements:[F::ZERO;4]};
        for level in 0..t.siblings.len() {
            let s=proof_siblings.get(level);
            for j in 0..3 {
                let val=if fault=="sibling"&&level==0&&j==0
                    {HashOut{elements:[f(300);4]}}
                    else{s.map(|x|x[j]).unwrap_or(zero_hash)};
                w.set_hash_target(t.siblings[level][j],val).unwrap();
            }
            w.set_target(t.positions[level],f(if fault=="invalid_position"&&level==0
                {4}else{proof_positions.get(level).copied().unwrap_or(0) as u64})).unwrap();
        }
        w.set_hash_target(t.root,if fault=="root"
            {HashOut{elements:[f(99);4]}} else {root}).unwrap();
        w.set_hash_target(t.chain,if fault=="zero_chain"
            {zero_hash}else if fault=="foreign_chain"
            {HashOut{elements:[f(200);4]}}else{chain}).unwrap();
        w.set_hash_target(t.nullifier,if fault=="nullifier"
            {HashOut{elements:[f(88);4]}}else{nullifier}).unwrap();
        w
    }
    fn rejects<T: std::fmt::Debug>(result:Result<T,impl std::fmt::Debug>)->bool{
        result.is_err()
    }
    #[test]
    fn dvn_v2_full_depth_actual_membership_depth_one_and_two() {
        let (data,t)=circuit(2);
        for depth in [1usize,2]{
            let proof=data.prove(fill(&t,depth,""))
                .expect("authentic sorted multi-level 4-ary path must prove");
            data.verify(proof.clone()).expect("nested Poseidon2 root verified");
            assert_eq!(proof.public_inputs.len(),15);
            assert_eq!(proof.public_inputs[12],f(300_000_001));
            assert_eq!(proof.public_inputs[13],f(199_999_998));
            assert_eq!(proof.public_inputs[14],f(1));
            let mut changed=proof;
            changed.public_inputs[0]=f(999);
            assert!(data.verify(changed).is_err(),"public root cannot change after proving");
        }
    }
    #[test]
    fn dvn_v2_full_depth_rejects_wrong_root_wrong_sibling_domain_or_amount() {
        use std::panic::{catch_unwind,AssertUnwindSafe};
        let (data,t)=circuit(2);
        for fault in ["root","sibling","foreign_chain","zero_chain",
                      "nullifier","inflation","zero_depth","invalid_position"] {
            let witness=fill(&t,2,fault);
            let outcome=catch_unwind(AssertUnwindSafe(||data.prove(witness)));
            assert!(outcome.is_err()||outcome.unwrap().is_err(),
                "Invalid V2 path, chain/nullifier tag or amount generated a valid proof: {fault}");
        }
        assert_eq!(DVN_NATIVE_MAX,100_000_000*100_000_000);
    }
    #[test]
    fn dvn_v2_full_depth_circuit_obeys_upstream_depth_limit(){
        assert!(MAX_DEPTH>=2);
    }
}
''';

def patch(root:Path)->None:
    source=root/"wormhole/circuit/src/devnira_v2_amount_circuit.rs"
    s=source.read_text(encoding="utf-8")
    if MARKER in s:
        raise ValueError("V2 full-depth proof already staged")
    for marker in ("pub fn constrain_native_dvn_authenticated_spend",
                   "pub const DVN_NATIVE_MAX",
                   "pub fn constrain_native_dvn_value_conservation"):
        if marker not in s:
            raise ValueError("Unsafe missing native exact-value proof dependency: "+marker)
    source.write_text(s+"\n"+RUST,encoding="utf-8")
    print("Plonky2 V2 variable-depth root proof staged for REAL Rust verification; on-chain activation NOT done.")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("pinned_circuit_source",type=Path)
    patch(p.parse_args().pinned_circuit_source)
