"""DVN amount-to-ZK-leaf bounds reference. Not a proof circuit implementation.

The upstream leaf packs the quantized amount in a u32; compatibility requires
*both* exact granularity and range. Changing only the quantum is unsafe.
"""
from dataclasses import dataclass

DVN_UNIT = 100_000_000
MAX_SUPPLY_UNITS = 100_000_000 * DVN_UNIT
MAX_LEAF_AMOUNT = (1 << 32) - 1
VESTED_ALLOCATION_UNITS = 7_000_000 * DVN_UNIT
MONTHLY_INSTALLMENT_UNITS = VESTED_ALLOCATION_UNITS // 12
FINAL_MONTH_UNITS = VESTED_ALLOCATION_UNITS - 11 * MONTHLY_INSTALLMENT_UNITS

@dataclass(frozen=True)
class LeafCompatibility:
    quantum: int
    max_exact_transfer_units: int
    supports_one_base_unit: bool
    can_encode_full_vesting_allocation: bool
    can_encode_exact_monthly_installment: bool

def assess_quantum(quantum: int) -> LeafCompatibility:
    if not isinstance(quantum, int) or isinstance(quantum, bool) or quantum <= 0:
        raise ValueError("quantum must be a positive integer")
    return LeafCompatibility(
        quantum=quantum,
        max_exact_transfer_units=quantum * MAX_LEAF_AMOUNT,
        supports_one_base_unit=quantum == 1,
        can_encode_full_vesting_allocation=(VESTED_ALLOCATION_UNITS % quantum == 0
            and VESTED_ALLOCATION_UNITS // quantum <= MAX_LEAF_AMOUNT),
        can_encode_exact_monthly_installment=(MONTHLY_INSTALLMENT_UNITS % quantum == 0
            and MONTHLY_INSTALLMENT_UNITS // quantum <= MAX_LEAF_AMOUNT),
    )

def assert_full_precision_and_range(quantum: int, max_transfer: int = MAX_SUPPLY_UNITS) -> None:
    cap = assess_quantum(quantum)
    if not cap.supports_one_base_unit:
        raise ValueError("ZK amount quantum loses DVN 8-decimal base-unit precision")
    if max_transfer > cap.max_exact_transfer_units:
        raise ValueError("ZK u32 leaf amount field cannot encode requested DVN transfers")
