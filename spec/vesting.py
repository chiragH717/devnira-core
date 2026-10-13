"""Exact DVN monthly vesting reference; not an on-chain implementation."""
from calendar import monthrange
from datetime import datetime, timezone

UNIT = 100_000_000
TOTAL_VESTED = 7_000_000 * UNIT
INSTANT = 3_000_000 * UNIT
MONTHS = 12

def add_calendar_months(start: datetime, months: int) -> datetime:
    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError("genesis must have timezone")
    if months < 0:
        raise ValueError("negative months")
    y = start.year + (start.month - 1 + months) // 12
    m = (start.month - 1 + months) % 12 + 1
    d = min(start.day, monthrange(y, m)[1])
    return start.replace(year=y, month=m, day=d)

def vested_total(genesis: datetime, at: datetime) -> int:
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("timestamp must have timezone")
    months = sum(at >= add_calendar_months(genesis, n) for n in range(1, MONTHS + 1))
    return (TOTAL_VESTED // MONTHS) * months if months < MONTHS else TOTAL_VESTED

def locked_total(genesis: datetime, at: datetime) -> int:
    return TOTAL_VESTED - vested_total(genesis, at)
