#!/usr/bin/env python3
"""Extend THE SAME authenticated 22-PI DVN proof to upstream MAX_DEPTH=16.

Test-only canonical 22PI secret/nullifier/4-ary Merkle/header/native fee proof.
Never activates proof verification, recursive VK, payout, transfer or mainnet.
Run AFTER patch_zk_v2_multilevel_authentic_22pi.py against exact pinned ZK SHA.
"""
import argparse
from pathlib import Path

MARKER="DEVNIRA_V2_22PI_AUTHENTICATED_16_LEVEL_NATIVE_PROOF"
MAX_DEPTH=16

def exact_once(text,old,new):
    if text.count(old)!=1:
        raise ValueError("STOP: pinned 22PI Plonky2 proof semantics changed: "+old[:100])
    return text.replace(old,new)

RUST=r'''
    // DEVNIRA_V2_22PI_AUTHENTICATED_16_LEVEL_NATIVE_PROOF
    #[test]
    fn dvn_v2_full_leaf_22pi_canonical_max_depth_16_real_proof(){
        // The SAME 22PI proof contains private secret, Poseidon2 nullifier,
        // exact native amount + 4 bps fee, all 16 sorted 4-ary Merkle
        // levels, root-to-header hash. This is the *maximum* upstream depth.
        let (data,t)=build(16);
        let proof=data.prove(witness(&t,""))
            .expect("actual max-16-depth Plonky2 DVN spend must prove");
        data.verify(proof.clone())
            .expect("same pinned VK verifies authenticated full depth");
        assert_eq!(proof.public_inputs.len(),22);
        assert_eq!(proof.public_inputs[0],F::ZERO);
        assert_eq!(proof.public_inputs[1],f(300_000_001));
        assert_eq!(proof.public_inputs[2],f(199_799_999));
        assert_eq!(proof.public_inputs[3],f(4));
        assert_eq!(proof.public_inputs[20],f(7));
        assert_eq!(proof.public_inputs[21],f(500_000_000));
        let mut fake_history=proof;
        fake_history.public_inputs[16]=f(999);
        assert!(data.verify(fake_history).is_err());
    }
    #[test]
    fn dvn_v2_full_leaf_22pi_full_depth_wrong_sibling_position_and_root_rejected(){
        use std::panic::{catch_unwind,AssertUnwindSafe};
        let (data,t)=build(16);
        for attack in ["path","position","root","coherent_root","bad_fee",
                       "bad_remainder","nullifier","secret","input"]{
            let attempt=catch_unwind(AssertUnwindSafe(
                || data.prove(witness(&t,attack))));
            assert!(attempt.is_err() || attempt.unwrap().is_err(),
                "unsafe MAX_DEPTH native DVN proof accepted {attack}");
        }
    }
    #[test]
    fn dvn_v2_full_leaf_22pi_refuses_empty_or_17_depth_before_build(){
        use std::panic::{catch_unwind,AssertUnwindSafe};
        for invalid_depth in [0usize,17usize] {
            assert!(catch_unwind(AssertUnwindSafe(
                || build(invalid_depth))).is_err(),
                "out-of-range Merkle depth must fail: {invalid_depth}");
        }
    }
''';

def patch(root:Path):
    file=root/"wormhole/circuit/src/devnira_v2_amount_circuit.rs"
    if not file.is_file():
        raise ValueError("STOP: no actual pinned Plonky2 source")
    upstream=root/"common/src/zk_merkle.rs"
    code=file.read_text(encoding="utf-8")
    merkle=upstream.read_text(encoding="utf-8")
    if "pub const MAX_DEPTH: usize = 16;" not in merkle:
        raise ValueError("STOP: pinned upstream authenticated MAX_DEPTH changed")
    if MARKER in code:
        raise ValueError("Full-depth authenticated DVN 22PI tests already staged")
    for required in (
        "DEVNIRA V2 MULTI-LEVEL 22PI OWNER/HEADER TEST RESEARCH ONLY",
        "BlockHeader::conditional_block_hash_binding(",
        "Nullifier::conditional_hash_binding(",
        "UnspendableAccount::constraints(",
        "enforce_target_less_than_const(&mut b,remainder,10_000,14)",
        "assert_eq!(data.common.num_public_inputs,FELTS);",
        "fn dvn_v2_full_leaf_22pi_rejects_fake_spends_and_roots()",
    ):
        if required not in code:
            raise ValueError("STOP: missing canonical source dependency: "+required)
    code=exact_once(code,
        'assert!((1..=3).contains(&layers), "bounded authenticated path length");',
        'assert!((1..=16).contains(&layers), "bounded authenticated path length");')
    code=exact_once(code,
        '        assert!((1..=3).contains(&layers));',
        '        assert!((1..=16).contains(&layers));')
    test_name='    #[test]\n    fn dvn_v2_full_leaf_22pi_rejects_fake_spends_and_roots(){'
    code=exact_once(code,test_name,RUST+"\n"+test_name)
    file.write_text(code,encoding="utf-8")
    print("One pinned 22PI secret+fee+Merkle+header proof now supports full depth 16.")
    print("NO recursive proof, on-chain V2 verifier, payout, signed transfer or mainnet.")

if __name__=="__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("pinned_zk_source",type=Path)
    patch(cli.parse_args().pinned_zk_source)
