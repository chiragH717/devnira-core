"""Fail-closed DEVNIRA Windows wallet receive + finalized balance reader.

Only reads public chain data from a locally running, independently pinned
DEVNIRA runtime. No private key handling, signing or transaction submission.
Actual active 8-decimal independent genesis is required before use.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
import sys
import urllib.request

# Also importable when launched directly as `python wallet/devnira_windows.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spec.ss58_company_account import decode_ss58_account
from wallet.network_identity import HASH, validate_identity, validate_local_rpc

SYSTEM_ACCOUNT_STORAGE_PREFIX = bytes.fromhex(
    "26aa394eea5630e07c48ae0c9558cef7"
    "b99d880ec681799c0cf30e8886371da9"
)
UNIT = 100_000_000
MAX_SUPPLY_UNITS = 100_000_000 * UNIT

@dataclass(frozen=True)
class AccountBalance:
    """Public on-chain System.Account fields at one finalized block."""
    address: str
    genesis_hash: str
    at_finalized_hash: str
    nonce: int
    free_units: int
    reserved_units: int
    frozen_units: int
    @property
    def total_units(self) -> int:
        return self.free_units + self.reserved_units

def storage_key_for_account(address: str) -> str:
    """Substrate System.Account: Twox128(System) ++ Twox128(Account) ++
    Blake2_128Concat(32-byte AccountId). No rpc-owned storage key allowed.
    """
    from hashlib import blake2b
    account = decode_ss58_account(address, prefix=190)
    return "0x" + (
        SYSTEM_ACCOUNT_STORAGE_PREFIX + blake2b(account, digest_size=16).digest() + account
    ).hex()

def parse_system_account(value: object) -> tuple[int, int, int, int]:
    """Decode THIS pinned FRAME runtime only:
    AccountInfo { nonce: u32, consumers: u32, providers: u32,
    sufficients: u32, data: AccountData<u128> { free, reserved, frozen, flags } }.
    Never guess alternate runtime SCALE layouts.
    """
    if value is None:
        return 0, 0, 0, 0
    if not isinstance(value, str) or not re.fullmatch(r"0x(?:[0-9a-fA-F]{2})+", value):
        raise ValueError("Malformed System.Account SCALE response")
    raw = bytes.fromhex(value[2:])
    if len(raw) != 80:
        raise ValueError("Unexpected System.Account SCALE layout; refuse unverified balance")
    nonce = int.from_bytes(raw[0:4], "little")
    free = int.from_bytes(raw[16:32], "little")
    reserved = int.from_bytes(raw[32:48], "little")
    frozen = int.from_bytes(raw[48:64], "little")
    if any(n > MAX_SUPPLY_UNITS for n in (free, reserved, frozen)) or free + reserved > MAX_SUPPLY_UNITS:
        raise ValueError("Account balance exceeds DEVNIRA's 100M supply")
    return nonce, free, reserved, frozen

def format_dvn(units: int) -> str:
    if type(units) is not int or units < 0 or units > MAX_SUPPLY_UNITS:
        raise ValueError("Invalid DEVNIRA base-unit amount")
    return f"{units // UNIT:,}.{units % UNIT:08d} DVN"

def rpc(endpoint: str, method: str, params: list | None = None):
    validate_local_rpc(endpoint)
    req = urllib.request.Request(
        endpoint,
        json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params or []}).encode(),
        headers={"Content-Type":"application/json"},
    )
    with urllib.request.urlopen(req, timeout=8) as response:
        packet=json.load(response)
    if not isinstance(packet,dict) or packet.get("id") != 1 or packet.get("jsonrpc") != "2.0":
        raise ValueError("Unexpected local JSON-RPC response")
    if "error" in packet:
        raise RuntimeError(str(packet["error"]))
    if "result" not in packet:
        raise ValueError("Missing RPC result")
    return packet["result"]

def read_finalized_balance(
    endpoint: str,
    expected_genesis: str,
    address: str,
    *,
    rpc_fn=rpc,
) -> AccountBalance:
    """Never issue a balance RPC until caller provided genuine pinned genesis
    and structurally valid account. Identity is rechecked before state read.
    """
    validate_local_rpc(endpoint)
    if not isinstance(expected_genesis, str) or not HASH.fullmatch(expected_genesis):
        raise ValueError("Trusted independent DEVNIRA genesis pin is required")
    storage_key = storage_key_for_account(address)
    chain = rpc_fn(endpoint, "system_chain")
    version = rpc_fn(endpoint, "state_getRuntimeVersion")
    genesis = rpc_fn(endpoint, "chain_getBlockHash", [0])
    validate_identity(chain, version, genesis, expected_genesis)
    if version.get("specName") != "devnira-runtime":
        raise ValueError("Unexpected runtime name")
    properties = rpc_fn(endpoint, "system_properties")
    if not isinstance(properties, dict) or (
        properties.get("tokenSymbol"), properties.get("tokenDecimals"),
        properties.get("ss58Format"),
    ) != ("DVN", 8, 190):
        raise ValueError("Connected runtime metadata does not describe 8-decimal DVN / SS58 190")
    at = rpc_fn(endpoint, "chain_getFinalizedHead")
    if not isinstance(at, str) or not HASH.fullmatch(at):
        raise ValueError("Invalid finalized block hash")
    raw = rpc_fn(endpoint, "state_getStorage", [storage_key, at])
    nonce, free, reserved, frozen = parse_system_account(raw)
    return AccountBalance(address, genesis, at, nonce, free, reserved, frozen)
