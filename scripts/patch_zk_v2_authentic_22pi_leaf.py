#!/usr/bin/env python3
"""Opt-in REAL Plonky2 DVN V2 proof of an *integrated* 22-PI single-leaf spend.

This combines the pinned reference scheme's actual unspendable spend-secret
derivation, nullifier, native DVN value conservation, 4-ary Poseidon2 Merkle
path and canonical Poseidon2 block-header preimage in ONE leaf proof.
It is TEST-ONLY, not the 4.4 on-chain verifier/recursive aggregator. It cannot
settle funds, attest a historical block, set mining rewards or sign a wallet.
"""
import argparse
from pathlib import Path

MARKER = "DEVNIRA_V2_22PI_AUTHENTICATED_SPEND_HEADER_MERKLE_TEST_ONLY"

RUST = r'''
// DEVNIRA_V2_22PI_AUTHENTICATED_SPEND_HEADER_MERKLE_TEST_ONLY
#[cfg(test)]
mod devnira_v2_22pi_authenticated_spend_tests {
    use super::{constrain_native_dvn_authenticated_spend,DVN_NATIVE_MAX};
    use alloc::vec::Vec;
    use core::array;
    use plonky2::{
        field::types::Field,
        hash::{hash_types::{HashOut,HashOutTarget},poseidon2::Poseidon2Hash},
        iop::{target::Target,witness::{PartialWitness,WitnessWrite}},
        plonk::{circuit_builder::CircuitBuilder,circuit_data::{CircuitConfig,CircuitData},config::Hasher},
    };
    use zk_circuits_common::{
        circuit::{F,C,D},
        gadget_builder::GadgetBuilder,
        serialization::digest_to_bytes,
        gadgets::enforce_target_less_than_const,
        utils::string_to_felts,
    };
    use crate::block_header::{BlockHeader,BlockHeaderTargets};
    use crate::block_header::header::HeaderTargets;
    use crate::nullifier::{Nullifier,NullifierTargets, NULLIFIER_SALT};
    use crate::unspendable_account::{UnspendableAccount,UnspendableAccountTargets,UNSPENDABLE_SALT};

    const FELTS:usize=22;
    const TEST_FEE_BPS:u64=4;
    const V2_FEE_BPS:u64=4;
    struct AuthTargets {
        pi:[Target;FELTS],
        secret:HashOutTarget, account:HashOutTarget, count:[Target;2],
        fee:Target, remainder:Target, sibling:[HashOutTarget;3], position:Target,
        committed_root:HashOutTarget,
        parent:HashOutTarget, state:HashOutTarget, extrinsics:HashOutTarget,
        digest:[Target;28],
    }
    fn build()->(CircuitData<F,C,D>,AuthTargets){
        let mut b=CircuitBuilder::<F,D>::new(CircuitConfig::standard_recursion_config());
        // All 22 public targets registered FIRST; no hidden extra PI slots.
        let pi:[Target;FELTS]=array::from_fn(|_|b.add_virtual_target());
        b.register_public_inputs(&pi);
        let secret=b.add_virtual_hash();
        let account=b.add_virtual_hash();
        let count=array::from_fn(|_|b.add_virtual_target());
        let fee=b.add_virtual_target();
        let native=b.zero();
        b.connect(pi[0],native);
        let expected_rate=b.constant(F::from_canonical_u64(V2_FEE_BPS));
        b.connect(pi[3],expected_rate);
        // Bound exact 1e-8 native DVN values, and force genuine conservation.
        let leaf=constrain_native_dvn_authenticated_spend(&mut b,
            account.elements,count,pi[0],pi[21],pi[1],pi[2],fee);
        let nonzero_input=b.is_equal(pi[21],native);
        b.assert_zero(nonzero_input.target);
        // Prove 4 bps fee as an exact floor integer division, without
        // Goldilocks modular-overflow aliases. Enforce
        // input*4 = fee*10000 + remainder, 0 <= remainder < 10000.
        // cap 1e16 *4 =4e16 < Goldilocks. Explicitly cap the fee at
        // 4e12 before multiplication so fee*10000 < field prime as well.
        let remainder=b.add_virtual_target();
        let ten_thousand=b.constant(F::from_canonical_u64(10_000));
        b.range_check(remainder,14);
        enforce_target_less_than_const(&mut b,remainder,10_000,14);
        b.range_check(fee,42);
        enforce_target_less_than_const(&mut b,fee,4_000_000_000_001,42);
        let input_times_rate=b.mul(pi[21],expected_rate);
        let fee_times_denom=b.mul(fee,ten_thousand);
        let quotient_plus_rem=b.add(fee_times_denom,remainder);
        b.connect(input_times_rate,quotient_plus_rem);

        // Proven secret derives the SAME deposit leaf account and nullifier.
        UnspendableAccount::constraints(&UnspendableAccountTargets{
            account_id:account,secret},&mut b);
        let nullifier=NullifierTargets{
            hash:HashOutTarget{elements:array::from_fn(|i|pi[4+i])},
            secret,transfer_count:count,
        };
        let one=b.one();
        Nullifier::conditional_hash_binding(&nullifier,&mut b,one);

        // 4-ary Poseidon2 sibling-path membership, sorted-slot witness.
        // This proof intentionally supports one FULL level; variable-depth
        // and recursive aggregation still require a compatible single artifact.
        let position=b.add_virtual_target();
        b.range_check(position,2);
        let sibling=array::from_fn(|_|b.add_virtual_hash());
        let two=b.constant(F::from_canonical_u64(2));
        let three=b.constant(F::from_canonical_u64(3));
        let p0=b.is_equal(position,native);
        let p1=b.is_equal(position,one);
        let p2=b.is_equal(position,two);
        let p3=b.is_equal(position,three);
        let p01=b.or(p0,p1);
        let children:[HashOutTarget;4]=array::from_fn(|slot|
            HashOutTarget{elements:array::from_fn(|limb|match slot{
                0=>b.select(p0,leaf.elements[limb],sibling[0].elements[limb]),
                1=>{
                    let fallback=b.select(p0,sibling[0].elements[limb],sibling[1].elements[limb]);
                    b.select(p1,leaf.elements[limb],fallback)
                },
                2=>{
                    let fallback=b.select(p01,sibling[1].elements[limb],sibling[2].elements[limb]);
                    b.select(p2,leaf.elements[limb],fallback)
                },
                3=>b.select(p3,leaf.elements[limb],sibling[2].elements[limb]),
                _=>unreachable!(),
            })});
        let mut node_felts=Vec::with_capacity(16);
        for child in &children {node_felts.extend_from_slice(&child.elements);}
        let computed_root=b.poseidon2_hash_no_pad(node_felts);
        let committed_root=b.add_virtual_hash();
        for i in 0..4 {
            b.connect(computed_root.elements[i],committed_root.elements[i]);
        }
        // Actual upstream canonical block-header hash gadget. A fake root
        // cannot match both Merkle membership and the claimed header hash.
        let parent=b.add_virtual_hash();
        let state=b.add_virtual_hash();
        let extrinsics=b.add_virtual_hash();
        let digest=array::from_fn(|_|b.add_virtual_target());
        let header=HeaderTargets{
            parent_hash:parent.elements,
            block_number:pi[20],
            state_root:state.elements,
            extrinsics_root:extrinsics.elements,
            zk_tree_root:committed_root.elements,
            digest,
        };
        let block=BlockHeaderTargets {
            block_hash:HashOutTarget{elements:array::from_fn(|i|pi[16+i])},
            header,
        };
        BlockHeader::circuit_without_hash_binding(&block,&mut b);
        BlockHeader::conditional_block_hash_binding(&block,&mut b,one);
        let no_block=b.is_equal(pi[20],native);
        b.assert_zero(no_block.target);

        // Exit accounts are public native addresses; blank payout account
        // not permitted if corresponding output is positive.
        for (amount,start) in [(pi[1],8usize),(pi[2],12usize)] {
            let positive=b.is_equal(amount,native);
            let mut zero_address=b.one();
            for i in 0..4 {
                let is_zero=b.is_equal(pi[start+i],native);
                zero_address=b.mul(zero_address,is_zero.target);
            }
            let nonzero=b.sub(one,positive.target);
            let bad=b.mul(nonzero,zero_address);
            b.assert_zero(bad);
        }
        let data=b.build::<C>();
        assert_eq!(data.common.num_public_inputs,FELTS);
        (data,AuthTargets{pi,secret,account,count,fee,remainder,sibling,position,
                          committed_root,parent,state,extrinsics,digest})
    }
    fn f(n:u64)->F{F::from_canonical_u64(n)}
    fn double_hash(preimage:&[F])->HashOut<F>{
        let inner=Poseidon2Hash::hash_no_pad(preimage);
        Poseidon2Hash::hash_no_pad(&inner.elements)
    }
    fn secret_account(secret:[F;4])->HashOut<F>{
        let mut preimage=string_to_felts(UNSPENDABLE_SALT).unwrap();
        preimage.extend_from_slice(&secret);
        double_hash(&preimage)
    }
    fn nullifier(secret:[F;4],count:[F;2])->HashOut<F>{
        let mut preimage=string_to_felts(NULLIFIER_SALT).unwrap();
        preimage.extend_from_slice(&secret);
        preimage.extend_from_slice(&count);
        double_hash(&preimage)
    }
    fn make_path(account:HashOut<F>,amount:u64)->([HashOut<F>;3],u8,HashOut<F>){
        let leaf=Poseidon2Hash::hash_no_pad(&[
            account.elements[0],account.elements[1],
            account.elements[2],account.elements[3],
            f(0),f(1),f(0),f(amount)
        ]);
        let mut children=[leaf,Poseidon2Hash::hash_no_pad(&[f(61)]),
                          Poseidon2Hash::hash_no_pad(&[f(62)]),
                          Poseidon2Hash::hash_no_pad(&[f(63)])];
        children.sort_by_key(|h|digest_to_bytes(&h.elements));
        let pos=children.iter().position(|h|*h==leaf).unwrap();
        let neighbors:Vec<_>=children.iter().enumerate()
            .filter_map(|(i,h)|if i!=pos{Some(*h)}else{None}).collect();
        let mut preimage=Vec::with_capacity(16);
        for child in &children{preimage.extend_from_slice(&child.elements);}
        let root=Poseidon2Hash::hash_no_pad(&preimage);
        (neighbors.try_into().unwrap(),pos as u8,root)
    }
    fn make_block(root:HashOut<F>,height:F,parent:HashOut<F>,
                  state:HashOut<F>,extrinsics:HashOut<F>)->HashOut<F>{
        let mut preimage=Vec::with_capacity(45);
        preimage.extend_from_slice(&parent.elements);
        preimage.push(height);
        preimage.extend_from_slice(&state.elements);
        preimage.extend_from_slice(&extrinsics.elements);
        preimage.extend_from_slice(&root.elements);
        preimage.extend_from_slice(&[F::ZERO;28]);
        Poseidon2Hash::hash_no_pad(&preimage)
    }
    fn witness(t:&AuthTargets,fault:&str)->PartialWitness<F>{
        let secret=[f(101),f(102),f(103),f(104)];
        let count=[f(0),f(1)];
        let account=secret_account(secret);
        let nullifier=nullifier(secret,count);
        let actual_amount=if fault=="round"{500_000_001}else{500_000_000};
        let (siblings,pos,root)=make_path(account,actual_amount);
        let parent=Poseidon2Hash::hash_no_pad(&[f(1)]);
        let state=Poseidon2Hash::hash_no_pad(&[f(2)]);
        let extrinsics=Poseidon2Hash::hash_no_pad(&[f(3)]);
        let bh=make_block(root,f(7),parent,state,extrinsics);
        let mut values=[F::ZERO;FELTS];
        values[0]=F::ZERO;
        values[1]=f(if fault=="inflation"{300_000_002}else{300_000_001});
        values[2]=f(if fault=="round"{199_800_000}else{199_799_999});
        values[3]=f(if fault=="bps"{5}else{4});
        values[4..8].copy_from_slice(&nullifier.elements);
        for i in 0..4{
            values[8+i]=f(111+i as u64);
            values[12+i]=f(222+i as u64);
        }
        values[16..20].copy_from_slice(&bh.elements);
        values[20]=f(if fault=="height"{8}else{7});
        values[21]=f(if fault=="input"{500_000_001}else{actual_amount});
        if fault=="nullifier"{values[4]=f(999);}
        if fault=="block"{values[16]=f(999);}
        if fault=="account"{values[8]=F::ZERO;values[9]=F::ZERO;
                            values[10]=F::ZERO;values[11]=F::ZERO;}
        let mut w=PartialWitness::new();
        for (target,value) in t.pi.iter().zip(values) {
            w.set_target(*target,value).unwrap();
        }
        w.set_hash_target(t.secret,if fault=="secret"{
            HashOut{elements:[f(4),f(5),f(6),f(7)]}
        }else{HashOut{elements:secret}}).unwrap();
        w.set_hash_target(t.account,account).unwrap();
        w.set_target_arr(&t.count,&count).unwrap();
        w.set_target(t.fee,f(if fault=="bad_fee"{200_001}else{200_000})).unwrap();
        w.set_target(t.remainder,f(if fault=="round"{4}
            else if fault=="bad_remainder"{1}else{0})).unwrap();
        w.set_target(t.position,f(pos as u64)).unwrap();
        for (i,sib) in t.sibling.iter().enumerate(){
            w.set_hash_target(*sib,if fault=="path"&&i==0{
                HashOut{elements:[f(5);4]}
            }else{siblings[i]}).unwrap();
        }
        w.set_hash_target(t.committed_root,if fault=="root"{
            HashOut{elements:[f(55);4]}
        }else{root}).unwrap();
        w.set_hash_target(t.parent,parent).unwrap();
        w.set_hash_target(t.state,state).unwrap();
        w.set_hash_target(t.extrinsics,extrinsics).unwrap();
        for target in t.digest{w.set_target(target,F::ZERO).unwrap();}
        w
    }
    #[test]
    fn dvn_v2_full_leaf_22pi_owner_nullifier_merkle_header_proves(){
        let (data,t)=build();
        let proof=data.prove(witness(&t,""))
            .expect("valid test secret, membership and header must prove together");
        data.verify(proof.clone()).unwrap();
        assert_eq!(proof.public_inputs.len(),22);
        assert_eq!(proof.public_inputs[0],F::ZERO);
        assert_eq!(proof.public_inputs[1],f(300_000_001));
        assert_eq!(proof.public_inputs[2],f(199_799_999));
        // Fixed 4 bps policy charges 200,000 exact base units on 5 DVN.
        assert_eq!(500_000_000u64*TEST_FEE_BPS/10_000,200_000u64);
        assert!(DVN_NATIVE_MAX*TEST_FEE_BPS < 0xffff_ffff_0000_0001);
        let round=data.prove(witness(&t,"round"))
            .expect("rounding witness 5 DVN+1 base unit must prove");
        data.verify(round.clone()).unwrap();
        assert_eq!(round.public_inputs[21],f(500_000_001));
        assert_eq!(round.public_inputs[2],f(199_800_000));
        assert_eq!(proof.public_inputs[3],f(4));
        assert_eq!(proof.public_inputs[20],f(7));
        assert_eq!(proof.public_inputs[21],f(500_000_000));
        let mut changed=proof;
        changed.public_inputs[16]=f(999);
        assert!(data.verify(changed).is_err(),
            "cannot alter validated historical header commitment after proving");
        assert_eq!(DVN_NATIVE_MAX,10_000_000_000_000_000);
    }
    #[test]
    fn dvn_v2_full_leaf_22pi_rejects_fake_spends_and_roots(){
        use std::panic::{catch_unwind,AssertUnwindSafe};
        let (data,t)=build();
        for attack in ["inflation","bps","height","input","nullifier","block",
                       "account","secret","path","root","bad_fee","bad_remainder"]{
            let pw=witness(&t,attack);
            let r=catch_unwind(AssertUnwindSafe(||data.prove(pw)));
            assert!(r.is_err()||r.unwrap().is_err(),
                "cryptographically unbound native DVN spend: {attack}");
        }
    }
}
''';

def patch(root:Path)->None:
    proof=root/"wormhole/circuit/src/devnira_v2_amount_circuit.rs"
    code=proof.read_text(encoding="utf-8")
    if MARKER in code:
        raise ValueError("Integrated 22pi V2 candidate already staged")
    required=(
      "pub fn constrain_native_dvn_authenticated_spend(",
      "pub fn constrain_native_dvn_value_conservation(",
      "pub const DVN_NATIVE_MAX")
    for token in required:
        if token not in code:
            raise ValueError("Unsafe missing exact-u64 authenticated native leaf: "+token)
    for subfile,symbols in {
        "wormhole/circuit/src/block_header/mod.rs":
            ["pub fn conditional_block_hash_binding(", "pub fn circuit_without_hash_binding("],
        "wormhole/circuit/src/unspendable_account.rs":
            ["pub fn constraints(", "pub const UNSPENDABLE_SALT:"],
        "wormhole/circuit/src/nullifier.rs":
            ["pub fn conditional_hash_binding(", "pub const NULLIFIER_SALT:"],
        "wormhole/circuit/src/block_header/header.rs":
            ["pub struct HeaderTargets", "pub const DIGEST_LOGS_SIZE: usize = 110;"],
    }.items():
        upstream=(root/subfile).read_text(encoding="utf-8")
        for token in symbols:
            if token not in upstream:
                raise ValueError(f"Upstream signed-spend/header circuit semantics changed: {subfile} {token}")
    proof.write_text(code+"\n"+RUST,encoding="utf-8")
    print("Staged authentic 22-felt test leaf: deposit secret+nullifier+Merkle+header+native amount.")
    print("NOT A LIVE PRODUCTION PROVER, AGGREGATOR, FRAME VERIFIER OR SETTLEMENT.")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("pinned_plonky2_source",type=Path)
    patch(p.parse_args().pinned_plonky2_source)
