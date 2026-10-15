#!/usr/bin/env python3
"""Add TWO real recursive tiers: depth16 V2 leaf -> private -> public.

This constructs private batch circuits that bind the authenticated leaf VK,
then a public batch that binds a FIXED private VK; it verifies two genuinely
different secret-authorized leaves from one Merkle root and exports private
and public serialized proof/VK/common bytes. Development artifacts only.
All code is pinned native Plonky2; NO runtime dispatchable or production VK.
"""
from pathlib import Path
import argparse
MARKER = "DEVNIRA_V2_PRIVATE_PUBLIC_TWO_TIER_FIXED_KEY_AUTHENTICATED"
RUST=r'''
    // DEVNIRA_V2_PRIVATE_PUBLIC_TWO_TIER_FIXED_KEY_AUTHENTICATED
    // Private aggregator: reused genuine 22PI leaf circuit + exact full16
    // Merkle/nullifier and constant inner VK from previous integration.
    // Public aggregator: verify 2 REAL private proofs against ONE immutable
    // private VK and enforce same block history/asset/BPS, distinct
    // nullifiers, u54 overflow boundaries, and no fee or payout forgery.
    fn dvn_v2_public_of_two_private_24pi(
        private:&CircuitData<F,C,D>,
    )->(CircuitData<F,C,D>,
       Vec<plonky2::plonk::proof::ProofWithPublicInputsTarget<D>>){
        assert_eq!(private.common.num_public_inputs,24,
            "canonical private ABI = 22 public leaf felts + exact payout/fee");
        let mut b=CircuitBuilder::<F,D>::new(CircuitConfig::standard_recursion_config());
        let fixed_private_vk=b.constant_verifier_data::<C>(&private.verifier_only);
        let mut targets=Vec::with_capacity(2);
        for _ in 0..2 {
            let p=b.add_virtual_proof_with_pis(&private.common);
            b.verify_proof::<C>(&p,&fixed_private_vk,&private.common);
            targets.push(p);
        }
        // Never aggregate private proofs referring to unrelated roots,
        // different ledger assets or fee policies in the same public exit.
        for slot in [0usize,3,16,17,18,19,20] {
            b.connect(targets[0].public_inputs[slot],
                      targets[1].public_inputs[slot]);
        }
        let mut all_nullifiers_equal=b.one();
        for limb in 4..8 {
            let same=b.is_equal(targets[0].public_inputs[limb],
                                targets[1].public_inputs[limb]);
            all_nullifiers_equal=b.mul(all_nullifiers_equal,same.target);
        }
        b.assert_zero(all_nullifiers_equal);
        let mut total_paid=b.zero();
        let mut total_fees=b.zero();
        let mut total_inputs=b.zero();
        for p in &targets {
            let pi=&p.public_inputs;
            b.register_public_inputs(pi);
            // Both private proofs are independently proven to bind
            // input == exit1+exit2+exact floor(4-bps input fee).
            // Public aggregate additionally enforces their private
            // declared totals equal the embedded authenticated leaf.
            let exits=b.add(pi[1],pi[2]);
            b.connect(pi[22],exits);
            let fee=b.sub(pi[21],exits);
            b.connect(pi[23],fee);
            total_paid=b.add(total_paid,pi[22]);
            total_fees=b.add(total_fees,pi[23]);
            total_inputs=b.add(total_inputs,pi[21]);
        }
        let must_equal=b.add(total_paid,total_fees);
        b.connect(total_inputs,must_equal);
        // With exactly 2 leaves and bound <= 10^16 each, all sums are
        // <2*10^16 < Goldilocks modulus: no modular wrap in this bound.
        let max=b.constant(F::from_canonical_u64(DVN_NATIVE_MAX));
        for v in [total_paid,total_fees,total_inputs] {
            b.range_check(v,54);
            let rem=b.sub(max,v);
            b.range_check(rem,54);
        }
        b.register_public_input(total_paid);
        b.register_public_input(total_fees);
        (b.build::<C>(),targets)
    }

    #[test]
    fn dvn_v2_private_public_aggregator_real_two_level_same_history(){
        let (inner,t)=build(16);
        let proof_a=inner.prove(witness(&t,"")).expect("first secret-bound leaf");
        let proof_b=inner.prove(witness(&t,"next_count"))
            .expect("second real leaf in same historical tree");
        inner.verify(proof_a.clone()).unwrap();
        inner.verify(proof_b.clone()).unwrap();
        assert_eq!(&proof_a.public_inputs[16..21],
                   &proof_b.public_inputs[16..21]);
        assert_ne!(&proof_a.public_inputs[4..8],
                   &proof_b.public_inputs[4..8]);

        // PRIVATE: each leaf verified AGAINST ONE fixed authenticated VK.
        let (private, leaf_targets)=dvn_v2_recursive_authenticated_22pi(&inner,1);
        let mut wa=PartialWitness::new();
        wa.set_proof_with_pis_target(&leaf_targets[0],&proof_a).unwrap();
        let pa=private.prove(wa).expect("private proof A");
        let mut wb=PartialWitness::new();
        wb.set_proof_with_pis_target(&leaf_targets[0],&proof_b).unwrap();
        let pb=private.prove(wb).expect("private proof B");
        private.verify(pa.clone()).expect("private fixed leaf VK A");
        private.verify(pb.clone()).expect("private fixed leaf VK B");
        assert_eq!(pa.public_inputs.len(),24);
        assert_eq!(pb.public_inputs.len(),24);

        // PUBLIC: both private proofs are checked against constant
        // PRIVATE verifier data, not caller-supplied virtual verifier.
        let (public, batch_targets)=dvn_v2_public_of_two_private_24pi(&private);
        let mut pw=PartialWitness::new();
        pw.set_proof_with_pis_target(&batch_targets[0],&pa).unwrap();
        pw.set_proof_with_pis_target(&batch_targets[1],&pb).unwrap();
        let public_proof=public.prove(pw).expect("real TWO-tier public aggregation");
        public.verify(public_proof.clone()).expect("real public fixed-key recursion");
        assert_eq!(public_proof.public_inputs.len(),50);
        assert_eq!(public_proof.public_inputs[48],f(999_600_000));
        assert_eq!(public_proof.public_inputs[49],f(400_000));
        let mut tampered=public_proof.clone();
        tampered.public_inputs[48]=f(999_600_001);
        assert!(public.verify(tampered).is_err());

        if let Ok(dir)=std::env::var("DEVNIRA_TEST_ARTIFACT_DIR") {
            let root=std::path::PathBuf::from(dir);
            std::fs::create_dir_all(&root).unwrap();
            let gates=plonky2::util::serialization::DefaultGateSerializer;
            std::fs::write(root.join("private-v2-24pi-proof.bin"),pa.to_bytes()).unwrap();
            std::fs::write(root.join("private-v2-24pi-other-proof.bin"),pb.to_bytes()).unwrap();
            std::fs::write(root.join("private-v2-24pi-vk.bin"),
                private.verifier_only.to_bytes().unwrap()).unwrap();
            std::fs::write(root.join("private-v2-24pi-common.bin"),
                private.common.to_bytes(&gates).unwrap()).unwrap();
            std::fs::write(root.join("public-v2-50pi-proof.bin"),
                public_proof.to_bytes()).unwrap();
            std::fs::write(root.join("public-v2-50pi-vk.bin"),
                public.verifier_only.to_bytes().unwrap()).unwrap();
            std::fs::write(root.join("public-v2-50pi-common.bin"),
                public.common.to_bytes(&gates).unwrap()).unwrap();
            // ARTIFACTS contain ONLY public proof and verifier data; never
            // witness, owner secret or actual mnemonic/private signing keys.
        }

        // Duplicate same private proof is a real cryptographic proof,
        // but public aggregator MUST reject repeated nullifiers.
        use std::panic::{catch_unwind,AssertUnwindSafe};
        let mut replay=PartialWitness::new();
        replay.set_proof_with_pis_target(&batch_targets[0],&pa).unwrap();
        replay.set_proof_with_pis_target(&batch_targets[1],&pa).unwrap();
        let replay_result=catch_unwind(AssertUnwindSafe(||public.prove(replay)));
        assert!(replay_result.is_err() || replay_result.unwrap().is_err(),
                "cross-private-batch nullifier replay accepted");

        // A proof built by the right ABI but an unrelated private VK
        // must not be accepted as an input to public aggregation.
        let mut fake_builder=CircuitBuilder::<F,D>::new(
            CircuitConfig::standard_recursion_config());
        let virtual_pi:Vec<Target>=(0..24)
            .map(|_|fake_builder.add_virtual_public_input()).collect();
        let foreign=fake_builder.build::<C>();
        let mut foreign_witness=PartialWitness::new();
        for p in &virtual_pi {
            foreign_witness.set_target(*p,F::ZERO).unwrap();
        }
        let foreign_proof=foreign.prove(foreign_witness).unwrap();
        let mut malicious=PartialWitness::new();
        malicious.set_proof_with_pis_target(&batch_targets[0],&pa).unwrap();
        malicious.set_proof_with_pis_target(&batch_targets[1],&foreign_proof).unwrap();
        let rejection=catch_unwind(AssertUnwindSafe(||public.prove(malicious)));
        assert!(rejection.is_err() || rejection.unwrap().is_err(),
            "public aggregator accepted a foreign private verifier key");
    }
'''
def patch(root:Path)->None:
    f=root/"wormhole/circuit/src/devnira_v2_amount_circuit.rs"
    if not f.is_file():
        raise ValueError("STOP: pinned Plonky2 source missing")
    s=f.read_text(encoding="utf-8")
    if MARKER in s:
        raise ValueError("STOP: private/public already applied")
    for required in ("DEVNIRA_V2_AUTHENTICATED_22PI_FIXED_VK_RECURSION",
        "fn dvn_v2_recursive_authenticated_22pi(",
        "fn dvn_v2_recursive22_two_distinct_real_nullifiers_aggregate_and_replay_fails()"):
        if required not in s:
            raise ValueError("STOP: prior authenticated fixed-VK recursive leaf is missing")
    target="    #[test]\n    fn dvn_v2_recursive22_rejects_same_abi_foreign_verifier_key() {"
    if s.count(target)!=1:
        raise ValueError("STOP: real foreign-key rejection test anchor drift")
    f.write_text(s.replace(target,RUST+"\n"+target,1),encoding="utf-8")
    print("STAGED: two-tier authenticated PRIVATE(24PI) -> PUBLIC(50PI), SAME header, distinct nullifiers, fixed keys and exact amounts.")
    print("CANDIDATE ONLY: verifier hashes and native test artifacts do NOT activate production keys, signed spend, or settlement.")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("pinned_zk",type=Path)
    patch(p.parse_args().pinned_zk)
