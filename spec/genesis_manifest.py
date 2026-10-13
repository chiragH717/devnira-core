"""Generate auditable DVN genesis allocation and calendar-month unlock manifest.

OFF-CHAIN PROPOSAL ONLY: not a FRAME genesis preset and not enforceable on chain.
Beneficiary public addresses must be independently validated in the runtime's address
format before final chain-spec generation. No secret keys are handled.
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Iterable

from spec.genesis_allocations import (
    Beneficiary, INSTANT_BUDGET, VESTED_BUDGET, validate_beneficiaries,
)
from spec.vesting import add_calendar_months

MONTHS = 12
UPSTREAM_MAX_GENESIS_SCHEDULES = 64

@dataclass(frozen=True)
class Unlock:
    beneficiary: str
    month: int
    unlock_timestamp_ms: int
    amount_units: int

def build_manifest(genesis: datetime, beneficiaries: Iterable[Beneficiary]) -> dict:
    if genesis.tzinfo is None or genesis.utcoffset() is None:
        raise ValueError("genesis must be timezone-aware")
    genesis = genesis.astimezone(timezone.utc)
    entries = sorted(validate_beneficiaries(beneficiaries), key=lambda b: b.public_address)
    schedules: list[Unlock] = []
    for entry in entries:
        if entry.vested_units == 0:
            continue
        monthly = entry.vested_units // MONTHS
        for month in range(1, MONTHS + 1):
            amount = monthly if month < MONTHS else entry.vested_units - monthly * (MONTHS - 1)
            if amount == 0:
                continue
            unlock = add_calendar_months(genesis, month)
            schedules.append(Unlock(
                beneficiary=entry.public_address,
                month=month,
                unlock_timestamp_ms=int(unlock.timestamp() * 1000),
                amount_units=amount,
            ))
    if len(schedules) > UPSTREAM_MAX_GENESIS_SCHEDULES:
        raise ValueError(
            f"{len(schedules)} schedules exceed upstream genesis limit "
            f"{UPSTREAM_MAX_GENESIS_SCHEDULES}; pallet change required"
        )
    if sum(s.amount_units for s in schedules) != VESTED_BUDGET:
        raise AssertionError("vesting schedule total mismatch")
    # Encode each monthly lump as a standard FRAME vesting schedule:
    # (beneficiary, start, cliff, end, amount) with cliff == end.
    # Upstream Pallet::vested_amount returns zero before the cliff and the
    # entire allocation at end. No interim linear payouts are possible.
    # These times are ABSOLUTE UTC milliseconds (not anchor offsets).
    genesis_ms = int(genesis.timestamp() * 1000)
    runtime_schedules = [
        [row.beneficiary, genesis_ms, row.unlock_timestamp_ms,
         row.unlock_timestamp_ms, row.amount_units]
        for row in schedules
    ]
    return {
        "schema": "devnira-genesis-allocation-manifest-v1",
        "production_genesis": False,
        "genesis_utc": genesis.isoformat(),
        "instant_total_units": INSTANT_BUDGET,
        "locked_total_units": VESTED_BUDGET,
        "beneficiaries": [asdict(entry) for entry in entries],
        "monthly_unlocks": [asdict(row) for row in schedules],
        "runtime_vesting_schedules_absolute_ms": runtime_schedules,
        "anchor_to_first_timestamp": False,
        "warning": "OFF-CHAIN ONLY: upstream vesting pallet supports cliff=end schedules, "
                   "but the grant amounts must meet the actual ZK quantum; on-chain genesis "
                   "integration, public address validation, governance restrictions, and tests remain.",
    }
