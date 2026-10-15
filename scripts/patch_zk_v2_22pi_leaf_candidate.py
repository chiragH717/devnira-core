#!/usr/bin/env python3
"""Opt-in pinned Plonky2 proof of exact native amount with the CANONICAL 22 PI leaf layout.

This is NOT an authenticated ownership, header-Merkle-root or on-chain
settlement proof: the 22 public values may otherwise be invented by a prover.
"""
import argparse
import re
from pathlib import Path

MARKER = "DEVNIRA_V2_22_FELT_NATIVE_PI_PROOF_CANDIDATE_NOT_ACTIVE"
ABI = {
    "PUBLIC_INPUTS_FELTS_LEN": 22,
    "ASSET_ID_INDEX": 0, "OUTPUT_AMOUNT_1_INDEX": 1,
    "OUTPUT_AMOUNT_2_INDEX": 2, "VOLUME_FEE_BPS_INDEX": 3,
    "NULLIFIER_START_INDEX": 4, "NULLIFIER_END_INDEX": 8,
    "EXIT_ACCOUNT_1_START_INDEX": 8, "EXIT_ACCOUNT_1_END_INDEX": 12,
    "EXIT_ACCOUNT_2_START_INDEX": 12, "EXIT_ACCOUNT_2_END_INDEX": 16,
    "BLOCK_HASH_START_INDEX": 16, "BLOCK_HASH_END_INDEX": 20,
    "BLOCK_NUMBER_INDEX": 20, "INPUT_AMOUNT_INDEX": 21,
}
RUST = r'''
// DEVNIRA_V2_22_FELT_NATIVE_PI_PROOF_CANDIDATE_NOT_ACTIVE
#[cfg(test)]
mod devnira_v2_22pi_layout_proof_tests {
    use super::constrain_native_dvn_authenticated_spend;
    use core::array;
    use plonky2::{
        field::types::Field,
        hash::poseidon2::Poseidon2Hash,
        iop::{target::Target, witness::{PartialWitness, WitnessWrite}},
        plonk::{circuit_builder::CircuitBuilder, circuit_data::{CircuitConfig,CircuitData}, config::Hasher},
    };
    use zk_circuits_common::{circuit::{F,C,D}, gadget_builder::GadgetBuilder};

    const DOMAIN: u64 = 0x4456_4e5f_5a4b_5632;
    const LEN:usize=22;
    struct Inputs {
        address:[Target;4], count:[Target;2],
        input:Target, out1:Target, out2:Target, fee:Target,
        pi:[Target;LEN],
    }
    fn build()->(CircuitData<F,C,D>,Inputs){
        let mut b=CircuitBuilder::<F,D>::new(CircuitConfig::standard_recursion_config());
        let address=array::from_fn(|_|b.add_virtual_target());
        let count=array::from_fn(|_|b.add_virtual_target());
        let input=b.add_virtual_target();
        let out1=b.add_virtual_target();
        let out2=b.add_virtual_target();
        let fee=b.add_virtual_target();
        let pi:[Target;LEN]=array::from_fn(|_|b.add_virtual_target());
        let native=b.zero();
        let leaf=constrain_native_dvn_authenticated_spend(
            &mut b,address,count,native,input,out1,out2,fee);
        b.connect(pi[0],native);
        b.connect(pi[1],out1);
        b.connect(pi[2],out2);
        let four=b.constant(F::from_canonical_u64(4));
        b.connect(pi[3],four);
        b.connect(pi[21],input);
        b.range_check(pi[20],32);
        let zero=b.zero();
        let empty=b.is_equal(input,zero);
        b.assert_zero(empty.target);
        // Only a commitment. Ownership AND trusted header root are NOT proven.
        let mut preimage=alloc::vec::Vec::with_capacity(9);
        let tag=b.constant(F::from_canonical_u64(DOMAIN));
        preimage.push(tag);
        preimage.extend_from_slice(&leaf.elements);
        preimage.extend_from_slice(&pi[16..20]);
        let digest=b.poseidon2_hash_no_pad(preimage);
        for i in 0..4{b.connect(pi[i+4],digest.elements[i]);}
        let mut zero_block=b.one();
        for limb in &pi[16..20]{
            let eq=b.is_equal(*limb,zero);
            zero_block=b.mul(zero_block,eq.target);
        }
        b.assert_zero(zero_block);
        b.register_public_inputs(&pi);
        let data=b.build::<C>();
        assert_eq!(data.common.num_public_inputs,LEN);
        (data,Inputs{address,count,input,out1,out2,fee,pi})
    }
    fn f(x:u64)->F{F::from_canonical_u64(x)}
    fn fill(t:&Inputs,fault:&str)->PartialWitness<F>{
        let mut w=PartialWitness::new();
        for (i,target) in t.address.iter().enumerate(){
            w.set_target(*target,f(100+i as u64)).unwrap();
        }
        w.set_target(t.count[0],f(0)).unwrap();
        w.set_target(t.count[1],f(1)).unwrap();
        let first=if fault=="inflation"{300_000_002}else{300_000_001};
        w.set_target(t.input,f(500_000_000)).unwrap();
        w.set_target(t.out1,f(first)).unwrap();
        w.set_target(t.out2,f(199_999_998)).unwrap();
        w.set_target(t.fee,f(1)).unwrap();
        let leaf=Poseidon2Hash::hash_no_pad(&[f(100),f(101),f(102),f(103),
                                             f(0),f(1),f(0),f(500_000_000)]);
        let block=[f(11),f(12),f(13),f(14)];
        let mut raw=alloc::vec![f(DOMAIN)];
        raw.extend_from_slice(&leaf.elements);
        raw.extend_from_slice(&block);
        let nullifier=Poseidon2Hash::hash_no_pad(&raw);
        let mut pi=[F::ZERO;LEN];
        pi[1]=f(first);pi[2]=f(199_999_998);pi[3]=f(if fault=="fee_rate"{5}else{4});
        for i in 0..4{
            pi[4+i]=nullifier.elements[i];
            pi[8+i]=f(1000+i as u64);
            pi[12+i]=f(2000+i as u64);
            pi[16+i]=block[i];
        }
        pi[20]=f(7);pi[21]=f(500_000_000);
        if fault=="nullifier"{pi[4]=f(99);}
        if fault=="block_hash"{pi[16]=f(99);}
        if fault=="input_amount"{pi[21]=f(500_000_001);}
        for (target,value) in t.pi.iter().zip(pi){
            w.set_target(*target,value).unwrap();
        }
        w
    }
    #[test]
    fn dvn_v2_22pi_exact_native_layout_proof_and_tamper_check(){
        let (data,t)=build();
        let proof=data.prove(fill(&t,"")).expect("Plonky2 22 public fields must prove");
        data.verify(proof.clone()).expect("same valid proof must verify");
        assert_eq!(proof.public_inputs.len(),22);
        assert_eq!(proof.public_inputs[0],f(0));
        assert_eq!(proof.public_inputs[1],f(300_000_001));
        assert_eq!(proof.public_inputs[2],f(199_999_998));
        assert_eq!(proof.public_inputs[3],f(4));
        assert_eq!(proof.public_inputs[20],f(7));
        assert_eq!(proof.public_inputs[21],f(500_000_000));
        let mut tampered=proof;
        tampered.public_inputs[21]=f(500_000_001);
        assert!(data.verify(tampered).is_err());
    }
    #[test]
    fn dvn_v2_22pi_bad_commitments_and_amounts_do_not_prove(){
        use std::panic::{catch_unwind,AssertUnwindSafe};
        let (data,t)=build();
        for invalid in ["inflation","nullifier","block_hash","input_amount","fee_rate"]{
            let outcome=catch_unwind(AssertUnwindSafe(||data.prove(fill(&t,invalid))));
            assert!(outcome.is_err()||outcome.unwrap().is_err(),
                "Invalid public-input witness was accepted: {invalid}");
        }
    }
}
''';

def patch(root:Path)->None:
    lib=root/"wormhole/circuit/src/devnira_v2_amount_circuit.rs"
    source=lib.read_text(encoding="utf-8")
    if MARKER in source:
        raise ValueError("22 PI proof already staged")
    for needed in ("pub const DVN_NATIVE_MAX", "pub fn constrain_native_dvn_authenticated_spend(",
                   "pub fn constrain_native_dvn_value_conservation("):
        if needed not in source:
            raise ValueError("Missing native amount-proving dependency: "+needed)
    upstream=(root/"wormhole/inputs/src/lib.rs").read_text(encoding="utf-8")
    for name,value in ABI.items():
        if re.search(rf"pub const {name}: usize = {value};",upstream) is None:
            raise ValueError("STOP: canonical 22 PI leaf drift: "+name)
    lib.write_text(source+"\n"+RUST,encoding="utf-8")
    print("Prove exact 22-felt layout candidate; NOT active, sender/root authorization absent.")

if __name__=="__main__":
    args=argparse.ArgumentParser()
    args.add_argument("pinned_zk_source",type=Path)
    patch(args.parse_args().pinned_zk_source)
