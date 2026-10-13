import unittest
from datetime import datetime, timezone
from spec.vesting import INSTANT, TOTAL_VESTED, add_calendar_months, vested_total, locked_total

class VestingTests(unittest.TestCase):
    def setUp(self):
        self.genesis = datetime(2027, 1, 31, 12, tzinfo=timezone.utc)
    def test_genesis(self):
        self.assertEqual(INSTANT, 300_000_000_000_000)
        self.assertEqual(vested_total(self.genesis, self.genesis), 0)
        self.assertEqual(locked_total(self.genesis, self.genesis), TOTAL_VESTED)
    def test_calendar_month(self):
        self.assertEqual(add_calendar_months(self.genesis, 1).day, 28)
        self.assertEqual(vested_total(self.genesis, datetime(2027, 2, 28, 11, tzinfo=timezone.utc)), 0)
        self.assertEqual(vested_total(self.genesis, datetime(2027, 2, 28, 12, tzinfo=timezone.utc)), TOTAL_VESTED // 12)
    def test_full_unlock(self):
        end = add_calendar_months(self.genesis, 12)
        self.assertEqual(vested_total(self.genesis, end), TOTAL_VESTED)
        self.assertEqual(locked_total(self.genesis, end), 0)
        self.assertEqual(vested_total(self.genesis, add_calendar_months(self.genesis, 11)), (TOTAL_VESTED // 12)*11)
    def test_no_early_unlock(self):
        self.assertEqual(vested_total(self.genesis, datetime(2026, 1, 1, tzinfo=timezone.utc)), 0)

if __name__ == "__main__":
    unittest.main()
