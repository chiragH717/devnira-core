#!/usr/bin/env python3
"""Add DVN-specific accounting tests to the patched upstream mining pallet.

The legacy Quantus tests expect a different issuance formula; this integration
test suite exercises the actual patched FRAME storage and reward hooks instead.
"""
import argparse
from pathlib import Path

MARKER = "// BEGIN DEVNIRA MINING PALLET ACCOUNTING TESTS"
TESTS = r'''
// BEGIN DEVNIRA MINING PALLET ACCOUNTING TESTS
#[test]
fn dvn_block_reward_is_reserved_when_author_missing() {
    new_test_ext().execute_with(|| {
        System::set_block_number(1);
        let initial_issuance = Balances::total_issuance();
        MiningRewards::on_finalize(1);
        assert_eq!(MiningRewards::pending_subsidy(), 500_000_000);
        assert_eq!(MiningRewards::mined_subsidy(), 0);
        assert_eq!(MiningRewards::collected_fees(), 0);
        assert_eq!(Balances::total_issuance(), initial_issuance);

        MiningRewards::on_finalize(2);
        assert_eq!(MiningRewards::pending_subsidy(), 1_000_000_000);
        assert_eq!(MiningRewards::mined_subsidy(), 0);
    });
}

#[test]
fn dvn_quantum_deferred_rewards_settle_without_double_issuance() {
    new_test_ext().execute_with(|| {
        let initial = Balances::free_balance(&MINER_1.account_id());
        set_miner_preimage_digest(MINER_1.preimage());
        // Upstream leaf quantum 10^10; 20 * 5 DVN subsidies are
        // intentionally needed for one payable quantum in this mock.
        for block in 1u64..=20 {
            System::set_block_number(block);
            MiningRewards::on_finalize(block);
        }
        assert_eq!(MiningRewards::mined_subsidy(), 10_000_000_000);
        assert_eq!(MiningRewards::pending_subsidy(), 0);
        assert_eq!(Balances::free_balance(&MINER_1.account_id()),
            initial + 10_000_000_000);
        assert_eq!(MockProofRecorder::proof_count(), 1);
    });
}

#[test]
fn dvn_mining_cap_counts_reserved_and_minted_subsidies() {
    new_test_ext().execute_with(|| {
        // Reserve two base units of remaining mining issuance. Quantum
        // prevents the tiny remainder from being minted in this test.
        MinedSubsidy::<Test>::put(MiningCap::get() - 2);
        System::set_block_number(1);
        MiningRewards::on_finalize(1);
        assert_eq!(MiningRewards::pending_subsidy(), 2);
        assert_eq!(MiningRewards::mined_subsidy(), MiningCap::get() - 2);

        MiningRewards::on_finalize(2);
        assert_eq!(MiningRewards::pending_subsidy(), 2,
            "a reserved subsidy cannot be issued twice");
        assert_eq!(MiningRewards::mined_subsidy(), MiningCap::get() - 2);
    });
}

#[test]
fn dvn_fee_recycling_does_not_consume_subsidy_budget() {
    new_test_ext().execute_with(|| {
        MiningRewards::collect_transaction_fees(10_000_000_000);
        set_miner_preimage_digest(MINER_1.preimage());
        System::set_block_number(1);
        MiningRewards::on_finalize(1);
        assert_eq!(MiningRewards::mined_subsidy(), 0);
        assert_eq!(MiningRewards::pending_subsidy(), 500_000_000);
        assert_eq!(MiningRewards::collected_fees(), 0);
    });
}
// END DEVNIRA MINING PALLET ACCOUNTING TESTS
'''

def patch(root: Path) -> None:
    lib = root / "pallets/mining-rewards/src/lib.rs"
    mock = root / "pallets/mining-rewards/src/mock.rs"
    tests = root / "pallets/mining-rewards/src/tests.rs"
    lib_source = lib.read_text()
    if "pub type MinedSubsidy" not in lib_source or "pub type PendingSubsidy" not in lib_source:
        raise ValueError("Apply patch_reward_runtime.py first")
    mock_source = mock.read_text()
    original = "\tpub const EmissionDivisor: u128 = 50_000_000;"
    if mock_source.count(original) != 1:
        raise ValueError("Upstream mock emission divisor changed")
    if "pub const MiningCap:" in mock_source:
        raise ValueError("Already patched mock MiningCap")
    mock_source = mock_source.replace(original, original + "\n\tpub const MiningCap: u128 = 9_000_000_000_000_000;", 1)
    original = "\ttype MaxSupply = MaxSupply;"
    if mock_source.count(original) != 1:
        raise ValueError("Upstream mock config changed")
    mock_source = mock_source.replace(original, original + "\n\ttype MiningCap = MiningCap;", 1)
    test_source = tests.read_text()
    if MARKER in test_source:
        raise ValueError("Already patched tests")
    if "use crate::{mock::*," not in test_source:
        raise ValueError("Unexpected upstream test header")
    test_source = test_source.replace(
        "use crate::{mock::*,",
        "use crate::{mock::*, MinedSubsidy,",
        1,
    )
    # Writes last, after all guards passed.
    mock.write_text(mock_source)
    tests.write_text(test_source + TESTS)
    print("Added four FRAME miner accounting tests and mock MiningCap.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("upstream_root", type=Path)
    patch(ap.parse_args().upstream_root)
