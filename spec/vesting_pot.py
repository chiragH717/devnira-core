"""Derive the *actual* FRAME pallet_vesting sovereign account used by DVN.

Pinned upstream runtime configuration:
    pallet_vesting::Config::PalletId = PalletId(*b"qvesting")
FRAME PalletId::into_account_truncating() for AccountId32 encodes the 4-byte
module prefix "modl", the exact eight-byte pallet id, then zero pads to 32.
A caller-provided escrow address must NEVER be trusted as the vesting pot.

This fixes an off-chain genesis-audit hole: formerly an arbitrary funded
address could masquerade as the on-chain pot while satisfying 3M+7M accounting.
"""
from spec.ss58_company_account import encode_ss58_account, decode_ss58_account

FRAME_PALLET_ACCOUNT_PREFIX=b"modl"
VESTING_PALLET_ID=b"qvesting"
ACCOUNT_ID_BYTES=32

def vesting_pot_account_id() -> bytes:
    if len(VESTING_PALLET_ID)!=8:
        raise ValueError("FRAME pallet ID must be exactly 8 bytes")
    seed=FRAME_PALLET_ACCOUNT_PREFIX+VESTING_PALLET_ID
    return seed + bytes(ACCOUNT_ID_BYTES-len(seed))

def vesting_pot_ss58() -> str:
    return encode_ss58_account(vesting_pot_account_id(),prefix=190)

def verify_vesting_pot_address(address: str) -> str:
    if decode_ss58_account(address,prefix=190)!=vesting_pot_account_id():
        raise ValueError("Vesting pot is not the native FRAME pallet sovereign account")
    return address
