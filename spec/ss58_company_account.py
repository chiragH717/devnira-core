"""Strict Substrate SS58 public AccountId32 codec for DEVNIRA company treasury.

Public addresses only: this module never generates, handles, or accepts private
keys. SS58 checksum/network validation does not prove ownership, Dilithium
signing compatibility or readiness to allocate real company funds.
"""
from hashlib import blake2b

ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
INDEX = {char: i for i, char in enumerate(ALPHABET)}
DEVNIRA_SS58_PREFIX = 190
SS58_MAGIC = b"SS58PRE"

class InvalidCompanyAddress(ValueError):
    pass

def _prefix_bytes(prefix: int) -> bytes:
    if type(prefix) is not int or prefix < 0 or prefix > 16383:
        raise InvalidCompanyAddress("Invalid SS58 network prefix")
    if prefix < 64:
        return bytes((prefix,))
    return bytes((((prefix & 0xFC) >> 2) | 0x40,
                  ((prefix >> 8) & 0x3F) | ((prefix & 0x03) << 6)))

def _b58encode(data: bytes) -> str:
    value = int.from_bytes(data, "big")
    chars = ""
    while value:
        value, rem = divmod(value, 58)
        chars = ALPHABET[rem] + chars
    leading = len(data) - len(data.lstrip(b"\0"))
    return "1" * leading + chars

def _b58decode(value: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise InvalidCompanyAddress("Missing SS58 public address")
    result = 0
    for char in value:
        if char not in INDEX:
            raise InvalidCompanyAddress("Non-Base58 character in public address")
        result = result * 58 + INDEX[char]
    zeros = len(value) - len(value.lstrip("1"))
    return b"\0" * zeros + (result.to_bytes((result.bit_length() + 7) // 8, "big") if result else b"")

def encode_ss58_account(account_id: bytes, prefix: int=DEVNIRA_SS58_PREFIX) -> str:
    if not isinstance(account_id, bytes) or len(account_id) != 32 or not any(account_id):
        raise InvalidCompanyAddress("Public AccountId must be a nonzero 32-byte value")
    data = _prefix_bytes(prefix) + account_id
    checksum = blake2b(SS58_MAGIC + data, digest_size=64).digest()[:2]
    return _b58encode(data + checksum)

def decode_ss58_account(address: str, prefix: int=DEVNIRA_SS58_PREFIX) -> bytes:
    data = _b58decode(address)
    expected = _prefix_bytes(prefix)
    if len(data) != len(expected) + 32 + 2 or not data.startswith(expected):
        raise InvalidCompanyAddress("Incorrect SS58 network/account length; DEVNIRA prefix 190 required")
    payload, checksum = data[:-2], data[-2:]
    expected_checksum = blake2b(SS58_MAGIC + payload, digest_size=64).digest()[:2]
    if checksum != expected_checksum:
        raise InvalidCompanyAddress("SS58 checksum failed")
    account_id = payload[len(expected):]
    if not any(account_id):
        raise InvalidCompanyAddress("Zero public account is forbidden")
    if encode_ss58_account(account_id, prefix) != address:
        raise InvalidCompanyAddress("Non-canonical SS58 address")
    return account_id

def verified_company_public_address(address: str) -> str:
    """Validate structure ONLY, not account ownership or chain genesis."""
    decode_ss58_account(address, DEVNIRA_SS58_PREFIX)
    return address
