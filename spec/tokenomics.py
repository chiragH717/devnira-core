"""DEVNIRA consensus emission reference (NOT a blockchain runtime)."""
from functools import lru_cache

UNIT = 100_000_000
CAP = 100_000_000 * UNIT
TEAM_ALLOCATION = 10_000_000 * UNIT
MINING_CAP = CAP - TEAM_ALLOCATION
INITIAL_REWARD = 5 * UNIT
EPOCH_LENGTH = 50_000
REDUCTION_NUM = 399
REDUCTION_DEN = 400

@lru_cache(maxsize=None)
def epoch_reward(epoch: int) -> int:
    if epoch < 0:
        raise ValueError("negative epoch")
    return max(1, INITIAL_REWARD * pow(REDUCTION_NUM, epoch) // pow(REDUCTION_DEN, epoch))

def subsidy(height: int, already_mined: int) -> int:
    if height < 1 or not (0 <= already_mined <= MINING_CAP):
        raise ValueError("invalid height or issued supply")
    return min(epoch_reward((height - 1) // EPOCH_LENGTH), MINING_CAP - already_mined)
