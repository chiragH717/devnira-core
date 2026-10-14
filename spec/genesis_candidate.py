"""Strict DEVNIRA eight-decimal genesis *input* constructor (not chain genesis).

The output is an auditable payload for a FUTURE, independently compiled
FRAME genesis preset. It is intentionally not a ChainSpec and cannot launch
a blockchain. Only public information is accepted; signing ownership,
runtime-WASM hashes and a genuine chain-spec must be verified separately.
"""
from datetime import datetime, timezone
from spec.genesis_allocations import Beneficiary
from spec.genesis_manifest import build_manifest
from spec.ss58_company_account import verified_company_public_address
from spec.vesting_pot import vesting_pot_ss58

UNIT = 100_000_000
MAX_UNITS = 100_000_000 * UNIT
MINER_BUDGET = 90_000_000 * UNIT
LIQUID = 3_000_000 * UNIT
LOCKED = 7_000_000 * UNIT

class GenesisInputError(ValueError):
    pass

def construct_inputs(proposal: dict) -> dict:
    if not isinstance(proposal, dict):
        raise GenesisInputError("JSON object required")
    expected = {
        "chain_id": "devnira-mainnet-v1",
        "name": "DEVNIRA",
        "symbol": "DVN",
        "base_units_per_coin": UNIT,
        "max_supply_units": MAX_UNITS,
        "mining_allocation_units": MINER_BUDGET,
        "premine_units": LIQUID + LOCKED,
        "team_investor_founder_allocation_units": LIQUID + LOCKED,
    }
    for name, value in expected.items():
        if type(proposal.get(name)) is not type(value) or proposal.get(name) != value:
            raise GenesisInputError("Approved tokenomics mismatch: " + name)
    if proposal.get("initial_balances") != []:
        raise GenesisInputError("Cannot import premine/test accounts from another genesis")
    company = proposal.get("company_treasury")
    if not isinstance(company, dict):
        raise GenesisInputError("Company treasury configuration missing")
    if company.get("policy") != "single_company_controlled_public_account":
        raise GenesisInputError("Exactly one company-controlled treasury required")
    if type(company.get("instant_units")) is not int or company["instant_units"] != LIQUID:
        raise GenesisInputError("Company instant grant must be exactly 3M DVN")
    if type(company.get("locked_units")) is not int or company["locked_units"] != LOCKED:
        raise GenesisInputError("Company locked grant must be exactly 7M DVN")
    if type(company.get("monthly_unlock_count")) is not int or company["monthly_unlock_count"] != 12:
        raise GenesisInputError("Exactly twelve monthly cliffs required")
    addr = company.get("public_address")
    if not isinstance(addr, str) or not addr or addr != addr.strip():
        raise GenesisInputError("STOP: genuine company SS58-190 PUBLIC address is required")
    try:
        verified_company_public_address(addr)
    except ValueError as exc:
        raise GenesisInputError("STOP: wrong company SS58 address or checksum") from exc
    pot = vesting_pot_ss58()
    if addr == pot:
        raise GenesisInputError("Company beneficiary cannot be the vesting sovereign pot")
    stamp = proposal.get("genesis_timestamp_ms")
    if type(stamp) is not int or stamp <= 0 or stamp > 253402300799999:
        raise GenesisInputError("STOP: approved UTC genesis timestamp (milliseconds) required")
    try:
        genesis = datetime.fromtimestamp(stamp / 1000, timezone.utc)
    except (ValueError, OverflowError, OSError) as exc:
        raise GenesisInputError("UTC genesis timestamp out of supported range") from exc
    # Keep the month anchor to the nearest original millisecond.
    if int(genesis.timestamp() * 1000) != stamp:
        raise GenesisInputError("Genesis timestamp does not roundtrip to exact milliseconds")
    manifest = build_manifest(genesis, [Beneficiary(addr, LIQUID, LOCKED)])
    schedules = manifest["runtime_vesting_schedules_absolute_ms"]
    if len(schedules) != 12 or sum(row[4] for row in schedules) != LOCKED:
        raise GenesisInputError("Genesis cliff arithmetic failed")
    if [row[4] for row in schedules] != [LOCKED // 12] * 11 + [LOCKED - (LOCKED // 12) * 11]:
        raise GenesisInputError("Twelve monthly amounts disagree with approved policy")
    if sum(amount for _, amount in ((addr, LIQUID), (pot, LOCKED))) != LIQUID + LOCKED:
        raise GenesisInputError("Genesis issuance mismatch")
    return {
        "schema": "devnira-checked-genesis-inputs-v1",
        "runnable_chain_spec": False,
        "production_genesis": False,
        "requires_independent_company_ownership_proof": True,
        "requires_active_v2_native_wasm_runtime": True,
        "genesis_utc": genesis.isoformat(),
        "genesis_timestamp_ms": stamp,
        "company_public_ss58_190": addr,
        "sovereign_vesting_pot_ss58_190": pot,
        "initial_account_balances_units": [[addr, LIQUID], [pot, LOCKED]],
        "onchain_vesting_schedules_absolute_ms": schedules,
        "anchor_to_first_timestamp": False,
        "miner_allocation_not_preminted_units": MINER_BUDGET,
        "genesis_issued_units": LIQUID + LOCKED,
        "maximum_supply_units": MAX_UNITS,
        "disclaimer": "OFF-CHAIN INPUTS ONLY; runtime, genesis state root, custody ownership and chain spec are not verified",
    }
