import unittest
from datetime import datetime, timezone
from spec.genesis_allocations import Beneficiary, INSTANT_BUDGET, VESTED_BUDGET
from spec.genesis_manifest import build_manifest

class GenesisManifestTests(unittest.TestCase):
    def setUp(self):
        self.genesis = datetime(2027, 1, 31, 12, tzinfo=timezone.utc)

    def test_one_beneficiary_exact_amounts_and_month_boundary(self):
        m = build_manifest(self.genesis, [Beneficiary("public-a", INSTANT_BUDGET, VESTED_BUDGET)])
        unlocks = m["monthly_unlocks"]
        self.assertEqual(len(unlocks), 12)
        self.assertEqual(sum(x["amount_units"] for x in unlocks), VESTED_BUDGET)
        self.assertEqual(unlocks[0]["month"], 1)
        self.assertEqual(
            unlocks[0]["unlock_timestamp_ms"],
            int(datetime(2027, 2, 28, 12, tzinfo=timezone.utc).timestamp() * 1000),
        )
        self.assertEqual(unlocks[-1]["amount_units"], VESTED_BUDGET - (VESTED_BUDGET // 12) * 11)
        self.assertFalse(m["production_genesis"])
        self.assertFalse(m["anchor_to_first_timestamp"])
        tuples = m["runtime_vesting_schedules_absolute_ms"]
        self.assertEqual(len(tuples), 12)
        self.assertEqual(tuples[0][2], tuples[0][3])
        self.assertEqual(tuples[0][4], unlocks[0]["amount_units"])
        self.assertLess(tuples[0][1], tuples[0][2])

    def test_two_beneficiaries_preserve_splits(self):
        m = build_manifest(self.genesis, [
            Beneficiary("public-b", INSTANT_BUDGET // 2, VESTED_BUDGET // 2),
            Beneficiary("public-a", INSTANT_BUDGET - INSTANT_BUDGET // 2, VESTED_BUDGET - VESTED_BUDGET // 2),
        ])
        self.assertEqual([x["public_address"] for x in m["beneficiaries"]], ["public-a", "public-b"])
        self.assertEqual(len(m["monthly_unlocks"]), 24)
        self.assertEqual(sum(x["amount_units"] for x in m["monthly_unlocks"]), VESTED_BUDGET)

    def test_more_than_five_beneficiaries_fails_closed(self):
        rows = [Beneficiary(f"public-{i}", 0, 0) for i in range(6)]
        for i in range(6):
            rows[i] = Beneficiary(
                f"public-{i}",
                INSTANT_BUDGET // 6 + (INSTANT_BUDGET % 6 if i == 5 else 0),
                VESTED_BUDGET // 6 + (VESTED_BUDGET % 6 if i == 5 else 0),
            )
        with self.assertRaisesRegex(ValueError, "exceed upstream genesis limit"):
            build_manifest(self.genesis, rows)

    def test_no_fabricated_addresses(self):
        with self.assertRaisesRegex(ValueError, "At least one"):
            build_manifest(self.genesis, [])

if __name__ == "__main__":
    unittest.main()
