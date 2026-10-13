#!/usr/bin/env python3
"""Add tests for immutable genesis vesting and editable post-genesis schedules."""
import argparse
from pathlib import Path

MARKER = "// BEGIN DEVNIRA IMMUTABLE GENESIS GRANT TEST"
TESTS = r'''
// BEGIN DEVNIRA IMMUTABLE GENESIS GRANT TEST
#[test]
fn dvn_genesis_founder_schedule_cannot_be_cancelled_or_retargeted() {
    use crate::mock::*;
    use frame_support::{assert_noop, assert_ok};
    use sp_runtime::DispatchError;
    const START: u64 = 100_000;
    const END: u64 = 500_000;
    const TOTAL: u128 = 10_000_000;
    new_test_ext(vec![(BOB, START, END, END, TOTAL)]).execute_with(|| {
        assert_eq!(crate::ImmutableGenesisScheduleCount::<Test>::get(), 1);
        assert_noop!(
            Vesting::end_schedule(RuntimeOrigin::root(), 0),
            DispatchError::Other("ImmutableGenesisGrant")
        );
        assert_noop!(
            Vesting::retarget_schedule(RuntimeOrigin::root(), 0, CHARLIE),
            DispatchError::Other("ImmutableGenesisGrant")
        );
        set_time(END - 1);
        assert_noop!(
            Vesting::claim(RuntimeOrigin::signed(PINGER), 0),
            crate::Error::<Test>::NothingToClaim
        );
        set_time(END);
        assert_ok!(Vesting::claim(RuntimeOrigin::signed(PINGER), 0));
        assert_eq!(Balances::free_balance(&BOB), TOTAL);
    });
}
// END DEVNIRA IMMUTABLE GENESIS GRANT TEST
'''

def patch(root: Path):
    path = root / "pallets/vesting/src/tests.rs"
    src = path.read_text()
    if MARKER in src or "fn cliff_equals_end_is_all_at_once()" not in src:
        raise ValueError("Upstream test API changed or protection test already injected")
    path.write_text(src + TESTS)
    print("Injected immutable genesis grant integration test.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("upstream_root", type=Path)
    patch(ap.parse_args().upstream_root)
