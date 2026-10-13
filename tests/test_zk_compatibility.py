import unittest
from spec.zk_compatibility import (
    DVN_UNIT, MAX_LEAF_AMOUNT, VESTED_ALLOCATION_UNITS,
    MONTHLY_INSTALLMENT_UNITS, FINAL_MONTH_UNITS,
    assess_quantum, assert_full_precision_and_range,
)

class ZkPrecisionTests(unittest.TestCase):
    def test_upstream_quantum_loses_dvn_precision(self):
        leaf = assess_quantum(10_000_000_000)
        self.assertFalse(leaf.supports_one_base_unit)
        self.assertFalse(leaf.can_encode_exact_monthly_installment)
        with self.assertRaisesRegex(ValueError, "precision"):
            assert_full_precision_and_range(10_000_000_000)

    def test_dvn_cent_quantum_still_loses_smallest_unit(self):
        with self.assertRaisesRegex(ValueError, "precision"):
            assert_full_precision_and_range(1_000_000)

    def test_base_unit_quantum_overflows_u32(self):
        leaf = assess_quantum(1)
        self.assertTrue(leaf.supports_one_base_unit)
        self.assertEqual(leaf.max_exact_transfer_units, MAX_LEAF_AMOUNT)
        self.assertFalse(leaf.can_encode_full_vesting_allocation)
        self.assertFalse(leaf.can_encode_exact_monthly_installment)
        with self.assertRaisesRegex(ValueError, "u32"):
            assert_full_precision_and_range(1)

    def test_exact_monthly_totals(self):
        self.assertEqual(11 * MONTHLY_INSTALLMENT_UNITS + FINAL_MONTH_UNITS, VESTED_ALLOCATION_UNITS)
        self.assertEqual(DVN_UNIT, 100_000_000)

    def test_invalid_quantum(self):
        for q in [0, -1, True]:
            with self.assertRaises(ValueError):
                assess_quantum(q)

if __name__ == "__main__":
    unittest.main()
