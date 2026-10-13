import tempfile
import unittest
from pathlib import Path
from scripts.test_onchain_vesting import patch, test_source, START
from spec.vesting import add_calendar_months

class OnChainVestingSourceTests(unittest.TestCase):
    def test_exact_twelve_gregorian_cliffs(self):
        s = test_source()
        self.assertIn("dvn_twelve_calendar_month_cliffs_pay_only_when_due", s)
        self.assertIn("use crate::Schedules;", s)
        for month in range(1, 13):
            ms = int(add_calendar_months(START, month).timestamp() * 1000)
            self.assertIn(str(ms) + "u64", s)
        self.assertIn("START_MS, due, due, INSTALLMENT", s)
    def test_refuses_changed_upstream_and_duplicate_patch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            file = root / "pallets/vesting/src/tests.rs"
            file.parent.mkdir(parents=True)
            file.write_text("fn cliff_equals_end_is_all_at_once()")
            with self.assertRaisesRegex(ValueError, "Upstream vesting API changed"):
                patch(root)
            file.write_text("new_test_ext(\nfn cliff_equals_end_is_all_at_once()\nfn multiple_schedules_for_same_beneficiary_claim_independently()")
            patch(root)
            with self.assertRaisesRegex(ValueError, "already patched"):
                patch(root)

if __name__ == "__main__":
    unittest.main()
