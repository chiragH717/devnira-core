import unittest
from scripts.test_two_node_rpc import assert_two_nodes

GENESIS = "0x" + "a" * 64
A = {"genesis": GENESIS, "finalized_hash": "0x" + "b" * 64,
     "finalized_height": 10, "peer_count": 1}

class TwoNodeRpcTests(unittest.TestCase):
    def test_equal_heights_and_finalized_hash(self):
        assert_two_nodes(dict(A), dict(A))

    def test_differing_heights_can_be_caught_up_in_caller(self):
        newer = dict(A, finalized_height=11, finalized_hash="0x" + "c" * 64)
        assert_two_nodes(A, newer)

    def test_genesis_mismatch(self):
        with self.assertRaisesRegex(AssertionError, "different genesis"):
            assert_two_nodes(A, dict(A, genesis="0x" + "f" * 64))

    def test_unconnected_peers_rejected(self):
        with self.assertRaisesRegex(AssertionError, "one peer"):
            assert_two_nodes(A, dict(A, peer_count=0))

    def test_forked_finalization_rejected(self):
        with self.assertRaisesRegex(AssertionError, "forked"):
            assert_two_nodes(A, dict(A, finalized_hash="0x" + "d" * 64))

    def test_genesis_only_rejected(self):
        with self.assertRaisesRegex(AssertionError, "not advanced"):
            assert_two_nodes(A, dict(A, finalized_height=0))

if __name__ == "__main__":
    unittest.main()
