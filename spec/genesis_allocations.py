"""Genesis allocation validation for future chain-spec generation.

This validates public allocation inputs only; it does NOT produce a runtime genesis.
"""
from dataclasses import dataclass
from typing import Iterable

UNIT = 100_000_000
INSTANT_BUDGET = 3_000_000 * UNIT
VESTED_BUDGET = 7_000_000 * UNIT

@dataclass(frozen=True)
class Beneficiary:
    public_address: str
    instant_units: int
    vested_units: int

def validate_beneficiaries(entries: Iterable[Beneficiary]) -> list[Beneficiary]:
    rows = list(entries)
    if not rows:
        raise ValueError("At least one public beneficiary address is required")
    if len({x.public_address for x in rows}) != len(rows):
        raise ValueError("Duplicate beneficiary public address")
    for row in rows:
        if not row.public_address or not row.public_address.strip():
            raise ValueError("Missing beneficiary public address")
        if not isinstance(row.instant_units, int) or isinstance(row.instant_units, bool):
            raise ValueError("Invalid instant amount")
        if not isinstance(row.vested_units, int) or isinstance(row.vested_units, bool):
            raise ValueError("Invalid vested amount")
        if row.instant_units < 0 or row.vested_units < 0:
            raise ValueError("Negative allocation")
    if sum(x.instant_units for x in rows) != INSTANT_BUDGET:
        raise ValueError("Instant allocation must equal 3 million DVN")
    if sum(x.vested_units for x in rows) != VESTED_BUDGET:
        raise ValueError("Vested allocation must equal 7 million DVN")
    return rows
