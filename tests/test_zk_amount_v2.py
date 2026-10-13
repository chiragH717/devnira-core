import unittest
from spec.zk_amount_v2 import (
    GOLDILOCKS_P, MAX_SUPPLY_BASE_UNITS,
    encode_native_amount, decode_native_amount,
)

class ZkAmountV2Tests(unittest.TestCase):
    def test_exact_roundtrip_min_max(self):
        for amount in [0, 1, 100_000_000, 5 * 100_000_000,
                       58_333_333_333_333, MAX_SUPPLY_BASE_UNITS]:
            self.assertEqual(decode_native_amount(encode_native_amount(amount)), amount)
    def test_cap_below_goldilocks(self):
        self.assertLess(MAX_SUPPLY_BASE_UNITS, GOLDILOCKS_P)
        self.assertEqual(len(encode_native_amount(MAX_SUPPLY_BASE_UNITS)), 8)
    def test_rejects_wraparound_and_noncanonical(self):
        for invalid in [-1, MAX_SUPPLY_BASE_UNITS + 1]:
            with self.assertRaises(ValueError):
                encode_native_amount(invalid)
        with self.assertRaises(ValueError):
            decode_native_amount(GOLDILOCKS_P.to_bytes(8, "little"))
        with self.assertRaises(ValueError):
            decode_native_amount((MAX_SUPPLY_BASE_UNITS + 1).to_bytes(8, "little"))
    def test_rejects_noninteger(self):
        with self.assertRaises(TypeError):
            encode_native_amount(0.1)
        with self.assertRaises(TypeError):
            encode_native_amount(True)
    def test_byte_width(self):
        with self.assertRaises(ValueError):
            decode_native_amount(b"short")

if __name__ == "__main__":
    unittest.main()
