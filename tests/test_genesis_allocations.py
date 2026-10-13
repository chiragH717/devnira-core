import unittest
from spec.genesis_allocations import Beneficiary, validate_beneficiaries, INSTANT_BUDGET, VESTED_BUDGET

class GenesisAllocationTests(unittest.TestCase):
    def test_exact_split(self):
        rows = validate_beneficiaries([
            Beneficiary("public-address-a", INSTANT_BUDGET // 2, VESTED_BUDGET // 2),
            Beneficiary("public-address-b", INSTANT_BUDGET - INSTANT_BUDGET // 2, VESTED_BUDGET - VESTED_BUDGET // 2),
        ])
        self.assertEqual(len(rows), 2)
    def test_missing(self):
        with self.assertRaises(ValueError):
            validate_beneficiaries([])
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            validate_beneficiaries([Beneficiary("same", INSTANT_BUDGET, VESTED_BUDGET), Beneficiary("same", 0, 0)])
    def test_wrong_supply(self):
        with self.assertRaises(ValueError):
            validate_beneficiaries([Beneficiary("a", INSTANT_BUDGET, VESTED_BUDGET - 1)])
    def test_negative(self):
        with self.assertRaises(ValueError):
            validate_beneficiaries([Beneficiary("a", INSTANT_BUDGET + 1, -1)])

if __name__ == "__main__":
    unittest.main()
