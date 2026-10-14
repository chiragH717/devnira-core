#!/usr/bin/env python3
"""Inject real FRAME exact-pot tests into the patched Quantus vesting pallet.

These tests exercise actual on-chain currency movement, conservation of total
issuance, all 12 calendar-month grants and prevention of sub-ED pot reaping.
They are still mock-runtime tests, NOT DVN independent mainnet evidence.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from spec.vesting import add_calendar_months

START = datetime(2027, 1, 31, 12, tzinfo=timezone.utc)
MARKER = "// BEGIN DEVNIRA EXACT GENESIS POT CONSENSUS TESTS"

def generate_tests() -> str:
    start = int(START.timestamp() * 1000)
    due = [int(add_calendar_months(START, m).timestamp()*1000) for m in range(1,13)]
    due_literal = ", ".join(f"{n}u64" for n in due)
    return f"""
{MARKER}
#[test]
fn dvn_exact_pot_all_twelve_monthly_grants_mint_no_extra_ed() {{
    use crate::mock::*;
    use frame_support::{{assert_noop, assert_ok}};
    const START_MS: u64 = {start};
    const DUE: [u64; 12] = [{due_literal}];
    const LOCKED: u128 = 700_000_000_000_000;
    const MONTHLY: u128 = LOCKED / 12;
    let grants = DUE.iter().enumerate().map(|(i, &due)| {{
        let amount = if i == 11 {{ LOCKED - MONTHLY * 11 }} else {{ MONTHLY }};
        (BOB, START_MS, due, due, amount)
    }}).collect::<Vec<_>>();
    new_test_ext_exact(grants).execute_with(|| {{
        let issuance_before = Balances::total_issuance();
        assert_eq!(Balances::free_balance(&pot()), LOCKED);
        assert_eq!(Balances::free_balance(&BOB), 0);
        for (i, &due) in DUE.iter().enumerate() {{
            set_time(due - 1);
            assert_noop!(
                Vesting::claim(RuntimeOrigin::signed(PINGER), i as u64),
                crate::Error::<Test>::NothingToClaim,
            );
            set_time(due);
            assert_ok!(Vesting::claim(RuntimeOrigin::signed(PINGER), i as u64));
            let claimed = if i == 11 {{ LOCKED }} else {{ MONTHLY * (i as u128 + 1) }};
            assert_eq!(Balances::free_balance(&BOB), claimed);
            assert_eq!(Balances::free_balance(&pot()), LOCKED - claimed);
            assert_eq!(Balances::total_issuance(), issuance_before);
            assert_ok!(Vesting::do_try_state());
        }}
        assert_eq!(Balances::free_balance(&pot()), 0);
        assert_eq!(Balances::free_balance(&BOB), LOCKED);
        assert_eq!(Balances::total_issuance(), issuance_before);
    }});
}}

#[test]
fn dvn_exact_pot_prevents_premature_reaping_below_ed() {{
    use crate::mock::*;
    use frame_support::{{assert_noop, assert_ok}};
    // If the 1_000-unit grant were paid first, it would leave 1 base unit
    // in the pot, below the 1_000-unit ED: exact-pot mode MUST reject it.
    new_test_ext_exact(vec![
        (BOB, 100_000, 500_000, 500_000, 1_000),
        (TREASURY, 100_000, 500_001, 500_001, 1),
    ]).execute_with(|| {{
        let issuance_before = Balances::total_issuance();
        set_time(500_000);
        assert_noop!(
            Vesting::claim(RuntimeOrigin::signed(PINGER), 0),
            crate::Error::<Test>::PotUnderfunded
        );
        assert_eq!(Balances::free_balance(&pot()), 1_001);
        set_time(500_001);
        assert_ok!(Vesting::claim(RuntimeOrigin::signed(PINGER), 1));
        assert_eq!(Balances::free_balance(&pot()), 1_000);
        assert_ok!(Vesting::claim(RuntimeOrigin::signed(PINGER), 0));
        assert_eq!(Balances::free_balance(&pot()), 0);
        assert_eq!(Balances::free_balance(&BOB), 1_000);
        assert_eq!(Balances::total_issuance(), issuance_before);
        assert_ok!(Vesting::do_try_state());
    }});
}}
// END DEVNIRA EXACT GENESIS POT CONSENSUS TESTS
"""

def patch(root: Path) -> None:
    path = root / "pallets/vesting/src/tests.rs"
    source = path.read_text()
    if MARKER in source:
        raise ValueError("Already injected exact-pot genesis FRAME tests")
    if "fn cliff_equals_end_is_all_at_once()" not in source:
        raise ValueError("Upstream vesting test API changed")
    path.write_text(source + generate_tests())
    print("Injected exact-pot FRAME 12-month conservation and below-ED tests.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream_root", type=Path)
    patch(parser.parse_args().upstream_root)
