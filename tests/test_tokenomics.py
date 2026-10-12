import unittest
from spec.tokenomics import CAP, epoch_reward, subsidy

class TokenomicsTests(unittest.TestCase):
    def test_first_block(self):
        self.assertEqual(subsidy(1, 0), 500_000_000)
    def test_first_reduction(self):
        self.assertEqual(subsidy(50_001, 0), 498_750_000)
    def test_hard_cap(self):
        self.assertEqual(subsidy(1, CAP - 3), 3)
        self.assertEqual(subsidy(1, CAP), 0)
    def test_monotone(self):
        self.assertGreaterEqual(epoch_reward(100), epoch_reward(101))
    def test_tail(self):
        self.assertEqual(epoch_reward(100_000), 1)

if __name__ == "__main__":
    unittest.main()
