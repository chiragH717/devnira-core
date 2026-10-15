#!/usr/bin/env python3
"""Extend pinned, exact native authenticated V2 22-PI leaf to 1..3 Merkle levels.

Apply AFTER patch_zk_leaf_amount_v2, patch_zk_native_conservation, and
patch_zk_v2_authentic_22pi_leaf. No dispatchables, live prover/verifier,
production settlement, or arbitrary-depth security claims.
"""
from pathlib import Path
import argparse

MARKER = "// DEVNIRA V2 MULTI-LEVEL 22PI OWNER/HEADER TEST RESEARCH ONLY"

def one(source, old, new):
    if source.count(old) != 1:
        raise ValueError("STOP: pinned V2 22PI proof source drift at " + repr(old[:80]))
    return source.replace(old,new)

def patch(root: Path):
    file = root/"wormhole/circuit/src/devnira_v2_amount_circuit.rs"
    text = file.read_text(encoding="utf-8")
    if MARKER in text:
        raise ValueError("22PI multi-level extension already staged")
    if "DEVNIRA_V2_22PI_AUTHENTICATED_SPEND_HEADER_MERKLE_TEST_ONLY" not in text:
        raise ValueError("STOP: authenticated native 22PI proof missing")
    # The inherited pinned test has one independently computed Merkle level.
    # Rebuild the SAME proof instance with 1..3 rounds, NOT a different
    # unauthenticated public-root proof shape.
    text=one(text, "    const FELTS:usize=22;",
             "    const FELTS:usize=22;\n    "+MARKER)
    text=one(text,
        "fee:Target, remainder:Target, sibling:[HashOutTarget;3], position:Target,",
        "fee:Target, remainder:Target, siblings:Vec<[HashOutTarget;3]>, positions:Vec<Target>,")
    text=one(text,
        "    fn build()->(CircuitData<F,C,D>,AuthTargets){",
        """    fn build(layers:usize)->(CircuitData<F,C,D>,AuthTargets){
        assert!((1..=3).contains(&layers), "bounded authenticated path length");""")
    start="        // 4-ary Poseidon2 sibling-path membership, sorted-slot witness."
    stop="        let committed_root=b.add_virtual_hash();"
    if text.count(start)!=1 or text.count(stop)!=1:
        raise ValueError("STOP: anchored Merkle proof body changed")
    p=text.index(start);q=text.index(stop,p)
    replacement=r'''        // 4-ary Poseidon2 membership to the SAME private header root across
        // 1, 2 OR 3 real hashing levels, not a relayer-supplied root tag.
        // A separate production full-MAX_DEPTH circuit is still required.
        let mut current=leaf;
        let mut positions=Vec::with_capacity(layers);
        let mut siblings=Vec::with_capacity(layers);
        let two=b.constant(F::from_canonical_u64(2));
        let three=b.constant(F::from_canonical_u64(3));
        for _level in 0..layers {
            let position=b.add_virtual_target();
            b.range_check(position,2);
            let sibling=array::from_fn(|_|b.add_virtual_hash());
            let p0=b.is_equal(position,native);
            let p1=b.is_equal(position,one);
            let p2=b.is_equal(position,two);
            let p3=b.is_equal(position,three);
            let p01=b.or(p0,p1);
            let children:[HashOutTarget;4]=array::from_fn(|slot|
                HashOutTarget{elements:array::from_fn(|limb|match slot{
                    0=>b.select(p0,current.elements[limb],sibling[0].elements[limb]),
                    1=>{
                        let fallback=b.select(p0,sibling[0].elements[limb],sibling[1].elements[limb]);
                        b.select(p1,current.elements[limb],fallback)
                    },
                    2=>{
                        let fallback=b.select(p01,sibling[1].elements[limb],sibling[2].elements[limb]);
                        b.select(p2,current.elements[limb],fallback)
                    },
                    3=>b.select(p3,current.elements[limb],sibling[2].elements[limb]),
                    _=>unreachable!(),
                })});
            let mut node_felts=Vec::with_capacity(16);
            for child in &children {node_felts.extend_from_slice(&child.elements);}
            current=b.poseidon2_hash_no_pad(node_felts);
            positions.push(position);
            siblings.push(sibling);
        }
        let computed_root=current;
'''
    text=text[:p]+replacement+text[q:]
    text=one(text,
        "        (data,AuthTargets{pi,secret,account,count,fee,remainder,sibling,position,",
        "        (data,AuthTargets{pi,secret,account,count,fee,remainder,siblings,positions,")
    start="    fn make_path(account:HashOut<F>,amount:u64)->([HashOut<F>;3],u8,HashOut<F>){"
    stop="    fn make_block(root:HashOut<F>,height:F,parent:HashOut<F>,"
    if text.count(start)!=1 or text.count(stop)!=1:
        raise ValueError("STOP: original witness Merkle computation changed")
    p=text.index(start);q=text.index(stop,p)
    replacement=r'''    fn make_path(account:HashOut<F>,amount:u64,layers:usize)
        ->(Vec<[HashOut<F>;3]>,Vec<u8>,HashOut<F>){
        assert!((1..=3).contains(&layers));
        let mut current=Poseidon2Hash::hash_no_pad(&[
            account.elements[0],account.elements[1],
            account.elements[2],account.elements[3],
            f(0),f(1),f(0),f(amount)
        ]);
        let mut positions=Vec::new();
        let mut siblings=Vec::new();
        for level in 0..layers {
            let mut children=[current,
                Poseidon2Hash::hash_no_pad(&[f(61+level as u64*3)]),
                Poseidon2Hash::hash_no_pad(&[f(62+level as u64*3)]),
                Poseidon2Hash::hash_no_pad(&[f(63+level as u64*3)])];
            children.sort_by_key(|h|digest_to_bytes(&h.elements));
            let pos=children.iter().position(|h|*h==current).unwrap();
            let neighbors:Vec<_>=children.iter().enumerate()
                .filter_map(|(i,h)|if i!=pos{Some(*h)}else{None}).collect();
            let mut preimage=Vec::with_capacity(16);
            for child in &children{preimage.extend_from_slice(&child.elements);}
            current=Poseidon2Hash::hash_no_pad(&preimage);
            positions.push(pos as u8);
            siblings.push(neighbors.try_into().unwrap());
        }
        (siblings,positions,current)
    }
'''
    text=text[:p]+replacement+text[q:]
    text=one(text,
        "        let (siblings,pos,root)=make_path(account,actual_amount);",
        "        let (siblings,pos,root)=make_path(account,actual_amount,t.siblings.len());")
    text=one(text,
        "        w.set_target(t.position,f(pos as u64)).unwrap();\n        for (i,sib) in t.sibling.iter().enumerate(){\n            w.set_hash_target(*sib,if fault==\"path\"&&i==0{\n                HashOut{elements:[f(5);4]}\n            }else{siblings[i]}).unwrap();\n        }",
        """        for (i,target) in t.positions.iter().enumerate(){
            w.set_target(*target,f(if fault=="position"&&i==t.positions.len()-1{
                ((pos[i]+1)%4) as u64
            }else{pos[i] as u64})).unwrap();
        }
        for (level,targets) in t.siblings.iter().enumerate(){
            for (slot,target) in targets.iter().enumerate(){
                w.set_hash_target(*target,if fault=="path"&&level==t.siblings.len()-1&&slot==0{
                    HashOut{elements:[f(5);4]}
                }else{siblings[level][slot]}).unwrap();
            }
        }""")
    text=one(text,
        "        let (data,t)=build();",
        "        let (data,t)=build(2);")
    text=one(text,
        '                       "account","secret","path","root","bad_fee","bad_remainder"]',
        '                       "account","secret","path","position","root","bad_fee","bad_remainder"]')
    # Second test: depth 1 and 3 with the very same 22PI spend/proof gadget.
    target='    #[test]\n    fn dvn_v2_full_leaf_22pi_rejects_fake_spends_and_roots(){'
    if text.count(target)!=1:
        raise ValueError("STOP: no unique authenticated witness tests")
    text=text.replace(target, r'''    #[test]
    fn dvn_v2_full_leaf_22pi_one_and_three_levels_have_unchanged_pi(){
        for layers in [1usize,3usize] {
            let (data,t)=build(layers);
            let proof=data.prove(witness(&t,"")).expect("real 4-ary multi-level proof");
            data.verify(proof.clone()).unwrap();
            assert_eq!(proof.public_inputs.len(),22);
            assert_eq!(proof.public_inputs[20],f(7));
            assert_eq!(proof.public_inputs[21],f(500_000_000));
            let mut forged=proof;
            forged.public_inputs[16]=f(999);
            assert!(data.verify(forged).is_err());
        }
    }
    #[test]
    fn dvn_v2_full_leaf_22pi_rejects_wrong_deep_sibling_and_position(){
        use std::panic::{catch_unwind,AssertUnwindSafe};
        let (data,t)=build(3);
        for attack in ["path","position","root"]{
            let r=catch_unwind(AssertUnwindSafe(||data.prove(witness(&t,attack))));
            assert!(r.is_err()||r.unwrap().is_err(),
                "invalid deep Merkle witness became a valid spend: {attack}");
        }
    }
'''+target)
    if text.count(MARKER)!=1:
        raise ValueError("STOP: multi-level marker missing or duplicated")
    file.write_text(text,encoding="utf-8")
    print("Authenticated single leaf, canonical 22PI, depths 1/2/3, fixed tested fee. NO ON-CHAIN SETTLEMENT.")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("pinned_circuits",type=Path)
    patch(p.parse_args().pinned_circuits)
