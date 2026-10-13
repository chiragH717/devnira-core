#!/usr/bin/env python3
"""Inject a DEVNIRA 12-calendar-month on-chain vesting test into Quantus FRAME tests.

Test-only integration: uses the existing BOB mock beneficiary, never a real
mainnet allocation. Does not modify production pallet behavior or genesis.
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from spec.vesting import add_calendar_months

START = datetime(2027, 1, 31, 12, tzinfo=timezone.utc)
MONTHLY_TEST_AMOUNT = 1_000_000  # divisible by upstream mock payout quantum=1_000
MARKER = "// BEGIN DEVNIRA 12-MONTH INTEGRATION TEST"

def test_source() -> str:
    dates = [int(add_calendar_months(START, i).timestamp() * 1000) for i in range(1, 13)]
    start_ms = int(START.timestamp() * 1000)
    dates_text = ", ".join(f"{ms}u64" for ms in dates)
    return f"""
{MARKER}
// These Gregorian month boundaries are generated from 2027-01-31T12:00:00Z.
#[test]
fn dvn_twelve_calendar_month_cliffs_pay_only_when_due() {{
    use crate::mock::*;
    use crate::Schedules;
    use frame_support::{{assert_noop, assert_ok}};
    const START_MS: u64 = {start_ms};
    const MONTHS: [u64; 12] = [{dates_text}];
    const INSTALLMENT: u128 = {MONTHLY_TEST_AMOUNT};
    let schedules = MONTHS
        .iter()
        .map(|&due| (BOB, START_MS, due, due, INSTALLMENT))
        .collect::<Vec<_>>();
    new_test_ext(schedules).execute_with(|| {{
        let initial = Balances::free_balance(&BOB);
        assert_eq!(initial, 0);
        for (idx, &due) in MONTHS.iter().enumerate() {{
            set_time(due - 1);
            assert_eq!(Vesting::vested_amount(
                &Schedules::<Test>::get(idx as u64).expect("genesis schedule"), due - 1,
            ), 0);
            assert_noop!(
                Vesting::claim(RuntimeOrigin::signed(PINGER), idx as u64),
                crate::Error::<Test>::NothingToClaim
            );
            set_time(due);
            assert_ok!(Vesting::claim(RuntimeOrigin::signed(PINGER), idx as u64));
            assert_eq!(Balances::free_balance(&BOB),
                initial + (idx as u128 + 1) * INSTALLMENT);
            assert_eq!(Schedules::<Test>::get(idx as u64)
                .expect("genesis schedule").claimed, INSTALLMENT);
        }}
        assert_eq!(Balances::free_balance(&BOB), 12 * INSTALLMENT);
        assert_eq!(Balances::free_balance(&pot()), ExistentialDeposit::get());
    }});
}}
// END DEVNIRA 12-MONTH INTEGRATION TEST
"""

def patch(root: Path) -> None:
    path = root / "pallets/vesting/src/tests.rs"
    source = path.read_text()
    if MARKER in source:
        raise ValueError("Vesting test already patched")
    for required in ["new_test_ext(", "fn cliff_equals_end_is_all_at_once()", "fn multiple_schedules_for_same_beneficiary_claim_independently()"]:
        if required not in source:
            raise ValueError(f"Upstream vesting API changed: {required}")
    path.write_text(source + test_source())
    print("Injected DEVNIRA 12-month FRAME vesting mock integration test.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream_root", type=Path)
    patch(parser.parse_args().upstream_root)
