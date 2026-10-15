#!/usr/bin/env python3
"""Stage a REAL Plonky2 22PI output -> actual FRAME storage preflight test.

The fixture is exported by the pinned authenticated depth-16 recursive test.
This is only a read-only ABI/history bridge, NOT on-chain proof verification
or settlement. Never allow the fixture or test mock to authorize production.
"""
import argparse
from pathlib import Path

MARKER="DEVNIRA_V2_REAL_PROVEN_22PI_FRAME_ABI_READ_ONLY_BRIDGE"
TEST=r'''
// DEVNIRA_V2_REAL_PROVEN_22PI_FRAME_ABI_READ_ONLY_BRIDGE
#[cfg(test)]
mod devnira_real_recursive_proof_frame_bridge {
    use crate::mock::*;
    use sp_core::H256;

    fn real_proven_inputs() -> [u64;22] {
        let path=std::env::var("DEVNIRA_REAL_PROOF_PIS_TXT")
            .expect("real pinned Plonky2 proof fixture required");
        let raw=std::fs::read_to_string(path).expect("read cryptographic PI fixture");
        let nums:Vec<u64>=raw.split_whitespace().map(|x|
            x.parse::<u64>().expect("canonical decimal public felt")
        ).collect();
        assert_eq!(nums.len(),22,"NEVER accept 7PI or 15PI research layout");
        nums.try_into().expect("exact canonical 22PI")
    }

    #[test]
    fn dvn_real_recursive_proof_abi_22pi_matches_frame_history_and_replay_guards() {
        let pis=real_proven_inputs();
        assert_eq!(pis[0],0,"DVN native asset only");
        assert_eq!(pis[3],4,"research fee rate must be 4 bps");
        assert_eq!(pis[20],7,"explicit pinned development historical number");
        assert_eq!(pis[21],500_000_000,"exact native 8-decimal amount");
        let mut hash=[0u8;32];
        let mut nullifier=[0u8;32];
        for i in 0..4 {
            hash[8*i..8*i+8].copy_from_slice(&pis[16+i].to_le_bytes());
            nullifier[8*i..8*i+8].copy_from_slice(&pis[4+i].to_le_bytes());
        }
        new_test_ext().execute_with(|| {
            System::set_block_number(8);
            // The mock FRAME history explicitly trusts the SAME
            // cryptographically proved claimed header for ABI boundary test.
            // Only real FINALIZED chain history may supply it in production.
            frame_system::BlockHash::<Test>::insert(7u64,H256::from(hash));
            let issuance=Balances::total_issuance();
            assert!(Wormhole::devnira_v2_leaf_chain_preflight(&pis).is_ok(),
                    "proof-derived exact 22PI must match FRAME history ABI");
            assert_eq!(issuance,Balances::total_issuance(),
                       "READ ONLY: ABI bridge must never mint");
            assert!(!Wormhole::used_nullifiers(nullifier),
                    "READ ONLY: must not mark a nullifier");
            let mut changed=pis;
            changed[16]^=1;
            assert!(Wormhole::devnira_v2_leaf_chain_preflight(&changed).is_err(),
                    "forged historical block must fail");
            changed=pis;
            changed[2]+=1;
            assert!(Wormhole::devnira_v2_leaf_chain_preflight(&changed).is_err(),
                    "one extra DVN base unit must fail fee conservation");
            crate::pallet::UsedNullifiers::<Test>::insert(nullifier,true);
            assert!(Wormhole::devnira_v2_leaf_chain_preflight(&pis).is_err(),
                    "persisted nullifier replay must fail");
            assert_eq!(issuance,Balances::total_issuance(),
                       "no production balance writes in preflight");
        });
    }
}
'''

def patch(root:Path)->None:
    lib=root/"pallets/wormhole/src/lib.rs"
    tests=root/"pallets/wormhole/src/tests.rs"
    if not lib.is_file() or not tests.is_file():
        raise ValueError("STOP: pinned FRAME source missing")
    content=lib.read_text(encoding="utf-8")
    if "DEVNIRA_V2_22_PI_PREFLIGHT_NO_SETTLEMENT" not in content:
        raise ValueError("STOP: real FRAME 22PI read-only preflight missing")
    current=tests.read_text(encoding="utf-8")
    if MARKER in current:
        raise ValueError("STOP: real proof/FRAME bridge already staged")
    if "DEVNIRA_V2_PALLET_ABI_STORAGE_TESTS" not in current:
        raise ValueError("STOP: original authenticated history/replay tests absent")
    tests.write_text(current.rstrip()+"\n\n"+TEST,encoding="utf-8")
    print("STAGED: exact pinned native proof's real 22 felts -> FRAME historical BlockHash/UsedNullifiers ABI.")
    print("NO ACTIVE PROOF VERIFIER, NO ATOMIC SETTLEMENT, NO SIGNED SEND, NOT MAINNET.")

if __name__=="__main__":
    arg=argparse.ArgumentParser()
    arg.add_argument("pinned_chain",type=Path)
    patch(arg.parse_args().pinned_chain)
