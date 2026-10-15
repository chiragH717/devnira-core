#!/usr/bin/env python3
"""Compose the EXISTING depth-16 authenticated 22PI proof into a fixed-VK recursion.

This stages actual Plonky2 tests in the pinned wormhole circuit source.
It does NOT touch active FRAME V1 dispatchables, balances or mainnet keys.
Run after patch_zk_v2_authenticated_full_depth_16.py.
"""
import argparse
from pathlib import Path

MARKER = "DEVNIRA_V2_AUTHENTICATED_22PI_FIXED_VK_RECURSION"

RUST_TESTS = r'''
    // DEVNIRA_V2_AUTHENTICATED_22PI_FIXED_VK_RECURSION
    // Same 22PI/full-depth owner, nullifier, Merkle and history proof,
    // recursively verified against a CONSTANT inner verifier key.
    fn dvn_v2_recursive_authenticated_22pi(
        inner: &CircuitData<F,C,D>, count:usize
    ) -> (CircuitData<F,C,D>,
          Vec<plonky2::plonk::proof::ProofWithPublicInputsTarget<D>>) {
        assert!((1..=2).contains(&count), "only tested bounded leaf count");
        assert_eq!(inner.common.num_public_inputs,22,
                   "canonical authenticated leaf ABI must be 22 PI");
        let mut b=CircuitBuilder::<F,D>::new(CircuitConfig::standard_recursion_config());
        let vk=b.constant_verifier_data::<C>(&inner.verifier_only);
        let mut proofs=Vec::with_capacity(count);
        for _ in 0..count {
            let p=b.add_virtual_proof_with_pis(&inner.common);
            b.verify_proof::<C>(&p,&vk,&inner.common);
            proofs.push(p);
        }
        if count==2 {
            // PRODUCTION-CRITICAL: the two spends MUST refer to exactly the
            // SAME finalized historical header and fee policy; independent
            // self-valid roots at one height cannot authorize a shared batch.
            for slot in [0usize,3,16,17,18,19,20] {
                b.connect(proofs[0].public_inputs[slot],
                          proofs[1].public_inputs[slot]);
            }
            // Enforce that the two proof slots cannot claim the same
            // four-felt nullifier, even if their leaf proofs are genuine.
            let mut equal=b.one();
            for limb in 4..8 {
                let same=b.is_equal(proofs[0].public_inputs[limb],
                                    proofs[1].public_inputs[limb]);
                equal=b.mul(equal,same.target);
            }
            b.assert_zero(equal);
        }
        let mut total_payout=b.zero();
        let mut total_fee=b.zero();
        for proof in &proofs {
            let pi=&proof.public_inputs;
            b.register_public_inputs(pi);
            let exits=b.add(pi[1],pi[2]);
            total_payout=b.add(total_payout,exits);
            // Fee is constrained INSIDE the authenticated inner leaf:
            // input = output1 + output2 + exact fixed 4-bps fee.
            let fee=b.sub(pi[21],exits);
            total_fee=b.add(total_fee,fee);
        }
        // Two leaves are <= 2e16 before any addition, below Goldilocks p.
        // Disallow a single recursive batch over the 100M DVN cap.
        let total=b.add(total_payout,total_fee);
        // Portable on wasm32 AND native: DVN cap does not fit usize on
        // 32-bit targets. Both amount and (cap-amount) must be < 2^54.
        // Since Goldilocks modulus > 2^54 + cap, negative differences
        // wrap outside 54 bits and fail the circuit constraints.
        let cap=b.constant(F::from_canonical_u64(DVN_NATIVE_MAX));
        for value in [total_payout,total_fee,total] {
            b.range_check(value,54);
            let remaining=b.sub(cap,value);
            b.range_check(remaining,54);
        }
        b.register_public_input(total_payout);
        b.register_public_input(total_fee);
        (b.build::<C>(),proofs)
    }

    #[test]
    fn dvn_v2_recursive22_real_full16_authenticated_leaf_fixed_vk() {
        let (inner,t)=build(16);
        let original=inner.prove(witness(&t,"")).expect("real full-depth authenticated leaf");
        inner.verify(original.clone()).expect("inner proof verification");
        let (outer,targets)=dvn_v2_recursive_authenticated_22pi(&inner,1);
        let mut pw=PartialWitness::new();
        pw.set_proof_with_pis_target(&targets[0],&original).unwrap();
        let proof=outer.prove(pw).expect("real fixed-key recursive proof");
        outer.verify(proof.clone()).expect("recursive verification");
        assert_eq!(proof.public_inputs.len(),24);
        assert_eq!(proof.public_inputs[20],f(7));
        assert_eq!(proof.public_inputs[21],f(500_000_000));
        assert_eq!(proof.public_inputs[22],f(499_800_000));
        assert_eq!(proof.public_inputs[23],f(200_000));
        // A public output cannot be modified without invalidating recursion.
        let mut tampered=proof.clone();
        tampered.public_inputs[4]=f(999);
        assert!(outer.verify(tampered).is_err());

        // Public, test-only inner+outer verifier data; NEVER private witness.
        // These are not approved production verifier-key commitments.
        if let Ok(dir)=std::env::var("DEVNIRA_TEST_ARTIFACT_DIR") {
            let root=std::path::PathBuf::from(dir);
            std::fs::create_dir_all(&root).expect("artifact dir");
            std::fs::write(root.join("authenticated-22pi-real-leaf-proof.bin"),
                original.to_bytes()).unwrap();
            std::fs::write(root.join("authenticated-22pi-recursive-proof.bin"),
                proof.to_bytes()).unwrap();
            std::fs::write(root.join("authenticated-22pi-inner-vk.bin"),
                inner.verifier_only.to_bytes().expect("serialize inner VK")).unwrap();
            std::fs::write(root.join("authenticated-22pi-recursive-vk.bin"),
                outer.verifier_only.to_bytes().expect("serialize recursive VK")).unwrap();
            // Export the actual cryptographically proved canonical 22 PI felts.
            // FRAME consumes this fixture in read-only test mode; it MUST
            // independently verify proof bytes before authorizing settlement.
            use plonky2::field::types::PrimeField64;
            let pi_lines=original.public_inputs.iter()
                .map(|felt|felt.to_canonical_u64().to_string())
                .collect::<Vec<_>>().join("\n");
            std::fs::write(root.join("authenticated-22pi-real-leaf-pis.txt"),
                format!("{pi_lines}\n")).unwrap();
            let gates=plonky2::util::serialization::DefaultGateSerializer;
            std::fs::write(root.join("authenticated-22pi-inner-common.bin"),
                inner.common.to_bytes(&gates).expect("serialize inner common")).unwrap();
            std::fs::write(root.join("authenticated-22pi-recursive-common.bin"),
                outer.common.to_bytes(&gates).expect("serialize recursive common")).unwrap();
        }
    }

    #[test]
    fn dvn_v2_recursive22_two_distinct_real_nullifiers_aggregate_and_replay_fails() {
        use std::panic::{catch_unwind,AssertUnwindSafe};
        let (inner,t)=build(16);
        let first=inner.prove(witness(&t,"")).expect("first spend proof");
        let second=inner.prove(witness(&t,"next_count")).expect("second genuine count proof");
        assert_ne!(&first.public_inputs[4..8],&second.public_inputs[4..8]);
        assert_eq!(&first.public_inputs[16..21],&second.public_inputs[16..21],
                   "different owned deposits must have ONE historical root and header");
        inner.verify(first.clone()).unwrap();
        inner.verify(second.clone()).unwrap();
        let (batch,targets)=dvn_v2_recursive_authenticated_22pi(&inner,2);
        let mut pw=PartialWitness::new();
        pw.set_proof_with_pis_target(&targets[0],&first).unwrap();
        pw.set_proof_with_pis_target(&targets[1],&second).unwrap();
        let aggregate=batch.prove(pw).expect("two real secret-bound spends");
        batch.verify(aggregate.clone()).expect("genuine recursive batch");
        assert_eq!(aggregate.public_inputs.len(),46);
        assert_eq!(aggregate.public_inputs[44],f(999_600_000));
        assert_eq!(aggregate.public_inputs[45],f(400_000));
        // Export a second real, two-leaf recursion and its own exact VK.
        if let Ok(dir)=std::env::var("DEVNIRA_TEST_ARTIFACT_DIR") {
            let root=std::path::PathBuf::from(dir);
            std::fs::create_dir_all(&root).unwrap();
            std::fs::write(root.join("authenticated-22pi-two-leaf-proof.bin"),
                aggregate.to_bytes()).unwrap();
            std::fs::write(root.join("authenticated-22pi-two-leaf-vk.bin"),
                batch.verifier_only.to_bytes().unwrap()).unwrap();
            let gates=plonky2::util::serialization::DefaultGateSerializer;
            std::fs::write(root.join("authenticated-22pi-two-leaf-common.bin"),
                batch.common.to_bytes(&gates).unwrap()).unwrap();
        }
        let mut changed=aggregate;
        changed.public_inputs[44]=f(999_600_001);
        assert!(batch.verify(changed).is_err());

        // No amount of valid single-proof verification makes a second
        // spend with the SAME nullifier legal inside this batch.
        let mut replay=PartialWitness::new();
        replay.set_proof_with_pis_target(&targets[0],&first).unwrap();
        replay.set_proof_with_pis_target(&targets[1],&first).unwrap();
        let result=catch_unwind(AssertUnwindSafe(||batch.prove(replay)));
        assert!(result.is_err() || result.unwrap().is_err(),
                "same-nullifier duplicate authenticated spend accepted");
    }

    #[test]
    fn dvn_v2_recursive22_rejects_same_abi_foreign_verifier_key() {
        use std::panic::{catch_unwind,AssertUnwindSafe};
        let (inner,_) = build(16);
        let (outer,targets)=dvn_v2_recursive_authenticated_22pi(&inner,1);
        let mut malicious=CircuitBuilder::<F,D>::new(
            CircuitConfig::standard_recursion_config());
        let public:Vec<Target>=(0..22)
            .map(|_|malicious.add_virtual_public_input()).collect();
        let foreign=malicious.build::<C>();
        let mut fake=PartialWitness::new();
        for target in &public { fake.set_target(*target,F::ZERO).unwrap(); }
        let bogus=foreign.prove(fake).expect("trivial attacker circuit proves");
        assert_eq!(bogus.public_inputs.len(),22);
        let mut w=PartialWitness::new();
        w.set_proof_with_pis_target(&targets[0],&bogus).unwrap();
        let result=catch_unwind(AssertUnwindSafe(||outer.prove(w)));
        assert!(result.is_err() || result.unwrap().is_err(),
                "foreign 22PI circuit was accepted with real pinned verifier");
    }
'''

def once(text: str, before: str, after: str) -> str:
    if text.count(before) != 1:
        raise ValueError("STOP: pinned authenticated 22PI source drift: " + repr(before[:100]))
    return text.replace(before, after, 1)

def patch(root: Path) -> None:
    source = root / "wormhole/circuit/src/devnira_v2_amount_circuit.rs"
    merkle = root / "common/src/zk_merkle.rs"
    if not source.is_file() or not merkle.is_file():
        raise ValueError("STOP: pinned Plonky2 source tree required")
    text = source.read_text(encoding="utf-8")
    if MARKER in text:
        raise ValueError("STOP: fixed-VK authenticated recursion already staged")
    if "pub const MAX_DEPTH: usize = 16;" not in merkle.read_text(encoding="utf-8"):
        raise ValueError("STOP: upstream MAX_DEPTH diverged from reviewed 16")
    for required in (
        "DEVNIRA_V2_22PI_AUTHENTICATED_16_LEVEL_NATIVE_PROOF",
        "Nullifier::conditional_hash_binding(",
        "BlockHeader::conditional_block_hash_binding(",
        "enforce_target_less_than_const(&mut b,remainder,10_000,14)",
        "fn dvn_v2_full_leaf_22pi_rejects_fake_spends_and_roots()",
    ):
        if required not in text:
            raise ValueError("STOP: missing real authenticated 22PI source: " + required)
    # Make a second VALID full-depth leaf witness with a DIFFERENT transfer
    # count, consistently recomputing its leaf path, nullifier and header.
    text = once(text,
        "let count=[f(0),f(1)];",
        'let count=[f(0),f(if fault=="next_count"{2}else{1})];')
    text = once(text,
        "fn make_path(account:HashOut<F>,amount:u64,layers:usize)",
        "fn make_path(account:HashOut<F>,amount:u64,layers:usize,transfer_count:u64)")
    text = once(text,
        "f(0),f(1),f(0),f(amount)",
        "f(0),f(transfer_count),f(0),f(amount)")
    # Both valid leaf proofs MUST share a genuine level-1 two-deposit
    # Merkle tree, then identical ancestor paths. No fabricated second root.
    text = once(text,
        """        let mut current=Poseidon2Hash::hash_no_pad(&[
            account.elements[0],account.elements[1],
            account.elements[2],account.elements[3],
            f(0),f(transfer_count),f(0),f(amount)
        ]);""",
        """        assert!(transfer_count==1 || transfer_count==2);
        let leaf_for_count=|count:u64| Poseidon2Hash::hash_no_pad(&[
            account.elements[0],account.elements[1],
            account.elements[2],account.elements[3],
            f(0),f(count),f(0),f(amount)
        ]);
        let mut current=leaf_for_count(transfer_count);""")
    text = once(text,
        """            let mut children=[current,
                Poseidon2Hash::hash_no_pad(&[f(61+level as u64*3)]),
                Poseidon2Hash::hash_no_pad(&[f(62+level as u64*3)]),
                Poseidon2Hash::hash_no_pad(&[f(63+level as u64*3)])];""",
        """            let mut children=if level==0 {
                [current,leaf_for_count(if transfer_count==1{2}else{1}),
                 Poseidon2Hash::hash_no_pad(&[f(61)]),
                 Poseidon2Hash::hash_no_pad(&[f(62)])]
            }else{
                [current,
                 Poseidon2Hash::hash_no_pad(&[f(61+level as u64*3)]),
                 Poseidon2Hash::hash_no_pad(&[f(62+level as u64*3)]),
                 Poseidon2Hash::hash_no_pad(&[f(63+level as u64*3)])]
            };""")
    text = once(text,
        "make_path(account,actual_amount,t.siblings.len());",
        'make_path(account,actual_amount,t.siblings.len(),'
        'if fault=="next_count"{2}else{1});')
    anchor = '    #[test]\n    fn dvn_v2_full_leaf_22pi_rejects_fake_spends_and_roots(){'
    text = once(text,anchor,RUST_TESTS + "\n" + anchor)
    if text.count(MARKER)!=1:
        raise ValueError("STOP: recursion marker not exactly once")
    source.write_text(text,encoding="utf-8")
    print("STAGED: 22PI depth-16 -> fixed-key recursive Plonky2, two-leaf nullifier uniqueness and exact aggregate totals.")
    print("NOT ACTIVE: FRAME V2 verifier, persistent nullifiers, atomic settlement, 8-decimal signed Send or independent genesis.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pinned_zk_source",type=Path)
    patch(parser.parse_args().pinned_zk_source)
