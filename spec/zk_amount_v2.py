"""DEVNIRA proposed V2 ZK amount encoding, reference only (NOT a circuit).

For native DVN supply <= 10**16 base units, the entire amount fits in ONE
canonical Goldilocks field element and u64, so no precision is lost. Production
needs updated Poseidon2 leaf circuits, proof public inputs, verifier and wallet.
"""
GOLDILOCKS_P = 0xFFFF_FFFF_0000_0001
DVN_UNIT = 100_000_000
MAX_SUPPLY_BASE_UNITS = 100_000_000 * DVN_UNIT
U64_MAX = (1 << 64) - 1

assert MAX_SUPPLY_BASE_UNITS < GOLDILOCKS_P <= U64_MAX

def encode_native_amount(amount_units: int) -> bytes:
    """Canonical single-felt little-endian encoding; reject rather than saturate."""
    if isinstance(amount_units, bool) or not isinstance(amount_units, int):
        raise TypeError("native amount must be integer base units")
    if not 0 <= amount_units <= MAX_SUPPLY_BASE_UNITS:
        raise ValueError("amount exceeds DVN native supply bounds")
    return amount_units.to_bytes(8, "little")

def decode_native_amount(felt_le: bytes) -> int:
    if not isinstance(felt_le, bytes) or len(felt_le) != 8:
        raise ValueError("expected exactly 8 bytes")
    value = int.from_bytes(felt_le, "little")
    if value >= GOLDILOCKS_P or value > MAX_SUPPLY_BASE_UNITS:
        raise ValueError("noncanonical/out-of-range DVN amount")
    return value
