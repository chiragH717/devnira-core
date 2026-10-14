"""Deterministic integer-only pool accounting prototype.

NO QUIC listener, PoW verifier, chain payout confirmation or signing exists
here. Inserting a share is *not* proof of mining. An independently reviewed
consensus share validator must authorize any use outside tests.
"""
import re
from collections import defaultdict
from dataclasses import dataclass

_WORKER = re.compile(r"[a-zA-Z0-9._-]{1,64}\Z")
_ID = re.compile(r"[a-f0-9]{64}\Z")
MAX_WEIGHT = 2**128 - 1
DVN_CAP = 10_000_000_000_000_000


@dataclass(frozen=True)
class VerifiedShareRecord:
    worker: str
    share_id: str
    weight: int
    # External validator is NOT supplied by this project. This marker is for
    # application plumbing only; it is never treated as cryptographic proof.
    verifier_reference: str


class AccountingCandidate:
    def __init__(self):
        self._seen = set()
        self._weights = defaultdict(int)
        self._sealed = False

    def record_from_external_verifier(self, share: VerifiedShareRecord):
        if self._sealed:
            raise ValueError("Round already sealed")
        if not isinstance(share, VerifiedShareRecord):
            raise ValueError("Unexpected share object")
        if not isinstance(share.worker, str) or not _WORKER.fullmatch(share.worker):
            raise ValueError("Unsafe worker identifier")
        if not isinstance(share.share_id, str) or not _ID.fullmatch(share.share_id):
            raise ValueError("Share must carry a canonical 32-byte identifier")
        if not isinstance(share.verifier_reference, str) or not share.verifier_reference:
            raise ValueError("External validation reference required; no local PoW validator")
        if type(share.weight) is not int or share.weight <= 0 or share.weight > MAX_WEIGHT:
            raise ValueError("Invalid share weight")
        if share.share_id in self._seen:
            raise ValueError("Duplicate share/replay")
        if sum(self._weights.values()) + share.weight > MAX_WEIGHT:
            raise ValueError("Round share weight overflow")
        self._seen.add(share.share_id)
        self._weights[share.worker] += share.weight

    def preview_proportional_distribution(self, reward_units: int):
        """Deterministic largest-remainder preview; NOT a payment transaction."""
        if type(reward_units) is not int or not 0 <= reward_units <= DVN_CAP:
            raise ValueError("Reward exceeds approved native supply cap")
        total = sum(self._weights.values())
        if total == 0:
            raise ValueError("Cannot distribute an unverified/empty round")
        base = {name: reward_units * weight // total
                for name, weight in self._weights.items()}
        dust = reward_units - sum(base.values())
        remainder = sorted(self._weights,
                           key=lambda name: (-(reward_units * self._weights[name] % total), name))
        for worker in remainder[:dust]:
            base[worker] += 1
        assert sum(base.values()) == reward_units
        return dict(sorted(base.items()))

    def seal(self):
        self._sealed = True
