import unittest
from datetime import datetime, timezone
from spec.company_treasury import (
    CompanyTreasury, UnverifiedCompanyAddress, company_genesis_manifest,
)
from spec.genesis_allocations import INSTANT_BUDGET, VESTED_BUDGET

class CompanyTreasuryTests(unittest.TestCase):
    def setUp(self):
        self.tge = datetime(2027, 1, 31, 12, tzinfo=timezone.utc)

    def test_single_company_exact_genesis_and_12_months(self):
        # This is an inert TEST STRING, not a wallet address or mainnet key.
        schedule = company_genesis_manifest(self.tge, CompanyTreasury("test-company-public-account", True))
        self.assertFalse(schedule["production_genesis"])
        self.assertEqual(len(schedule["beneficiaries"]), 1)
        self.assertEqual(schedule["beneficiaries"][0]["instant_units"], INSTANT_BUDGET)
        self.assertEqual(schedule["beneficiaries"][0]["vested_units"], VESTED_BUDGET)
        self.assertEqual(schedule["company_spendable_at_genesis_units"], INSTANT_BUDGET)
        self.assertEqual(schedule["company_total_locked_at_genesis_units"], VESTED_BUDGET)
        self.assertEqual(len(schedule["monthly_unlocks"]), 12)
        self.assertEqual(sum(row["amount_units"] for row in schedule["monthly_unlocks"]), VESTED_BUDGET)
        self.assertEqual(schedule["monthly_unlocks"][-1]["amount_units"],
                         VESTED_BUDGET - 11 * (VESTED_BUDGET // 12))
        self.assertTrue(all(
            row[2] == row[3] for row in schedule["runtime_vesting_schedules_absolute_ms"]))

    def test_unverified_address_cannot_mint(self):
        for item in [
            CompanyTreasury("", False),
            CompanyTreasury("invented-address", False),
            CompanyTreasury(" ", True),
            CompanyTreasury(" test-address", True),
        ]:
            with self.assertRaises(UnverifiedCompanyAddress):
                company_genesis_manifest(self.tge, item)

if __name__ == "__main__":
    unittest.main()
