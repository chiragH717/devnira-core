"""Audit a candidate DEVNIRA chain-spec/genesis with explicit release blockers.

This checks *supplied* JSON values, not standalone declared tokenomics policy.
The submitted chain spec must have an actual independent chain identity and
proof of exact genesis issuance, company balances, locked founder schedules.
Without those fields, fail closed. Never substitute the upstream dev preset.
"""

from spec.ss58_company_account import InvalidCompanyAddress, verified_company_public_address

DVN_UNIT = 100_000_000
TOTAL_SUPPLY = 100_000_000 * DVN_UNIT
MINING_RESERVE = 90_000_000 * DVN_UNIT
GENESIS_LIQUID = 3_000_000 * DVN_UNIT
GENESIS_LOCKED = 7_000_000 * DVN_UNIT
GENESIS_ISSUED = GENESIS_LIQUID + GENESIS_LOCKED

class UnsafeGenesis(ValueError):
    pass

def audit_candidate(spec: dict, company_address: str, manifest: dict) -> dict:
    if not isinstance(spec, dict) or not isinstance(manifest, dict):
        raise UnsafeGenesis("actual parsed chain spec and vesting manifest required")
    if not company_address or not isinstance(company_address, str) or company_address.strip() != company_address:
        raise UnsafeGenesis("verified company public account required")
    try:
        verified_company_public_address(company_address)
    except InvalidCompanyAddress as exc:
        raise UnsafeGenesis(f"invalid DEVNIRA company public account: {exc}") from exc
    if manifest.get("production_genesis") is not True:
        raise UnsafeGenesis("off-chain vesting proposal is not an enacted genesis")
    if manifest.get("company_address_verified") is not True:
        raise UnsafeGenesis("company address ownership/network has not been verified")
    if spec.get("id") != "devnira-mainnet-v1" or spec.get("chainType") not in ("Live", "live"):
        raise UnsafeGenesis("not an independent DEVNIRA mainnet chain spec")
    props = spec.get("properties", {})
    if (props.get("tokenDecimals"), props.get("tokenSymbol"), props.get("ss58Format")) != (8, "DVN", 190):
        raise UnsafeGenesis("token metadata is not eight-decimal DVN")
    if spec.get("bootNodes"):
        raise UnsafeGenesis("production bootnode choices must be verified independently")
    runtime = spec.get("genesis", {}).get("runtime", {})
    if not isinstance(runtime, dict):
        raise UnsafeGenesis("missing runtime genesis")
    balances = runtime.get("balances", {}).get("balances", [])
    if not isinstance(balances, list) or not balances:
        raise UnsafeGenesis("missing on-chain genesis balances")
    balances_map = {}
    for row in balances:
        if not isinstance(row, list) or len(row) != 2 or not isinstance(row[0], str) or not isinstance(row[1], int) or isinstance(row[1], bool) or row[1] < 0:
            raise UnsafeGenesis("invalid on-chain balance entry")
        try:
            verified_company_public_address(row[0])
        except InvalidCompanyAddress as exc:
            raise UnsafeGenesis(f"invalid DEVNIRA genesis account: {exc}") from exc
        if row[0] in balances_map:
            raise UnsafeGenesis("duplicate genesis balance")
        balances_map[row[0]] = row[1]
    if company_address not in balances_map or balances_map[company_address] != GENESIS_LIQUID:
        raise UnsafeGenesis("company does not own exactly 3M liquid DVN at genesis")

    vesting = runtime.get("vesting", {})
    schedules = vesting.get("schedules")
    if not isinstance(schedules, list) or len(schedules) != 12:
        raise UnsafeGenesis("genesis must contain 12 actual on-chain schedules")
    if vesting.get("anchorToFirstTimestamp") is not False:
        raise UnsafeGenesis("calendar vesting must use absolute timestamps")
    for i, row in enumerate(schedules, 1):
        if not isinstance(row, list) or len(row) != 5:
            raise UnsafeGenesis("invalid on-chain vesting tuple")
        addr, start, cliff, end, amount = row
        if addr != company_address or not all(isinstance(x, int) and not isinstance(x, bool) for x in [start,cliff,end,amount]):
            raise UnsafeGenesis("wrong beneficiary or invalid vesting values")
        if not (0 < start < cliff == end) or amount <= 0:
            raise UnsafeGenesis("vesting schedule is not a locked monthly cliff")
        corresponding = manifest.get("runtime_vesting_schedules_absolute_ms", [])
        if len(corresponding) != 12 or row != corresponding[i - 1]:
            raise UnsafeGenesis("on-chain schedules differ from approved calendar vesting manifest")
    locked = sum(row[4] for row in schedules)
    if locked != GENESIS_LOCKED:
        raise UnsafeGenesis("seven million locked DVN not accounted for")
    total_issued = sum(balances_map.values())
    if total_issued != GENESIS_ISSUED:
        raise UnsafeGenesis("genesis must issue exactly 10M, including vesting pot funds")
    if manifest.get("instant_total_units") != GENESIS_LIQUID or manifest.get("locked_total_units") != GENESIS_LOCKED:
        raise UnsafeGenesis("manifest does not match approved founders allocation")
    # Substrate vesting pot must be backed by exact locked amounts; here
    # caller explicitly supplies that account; we do not guess it.
    pot = manifest.get("onchain_vesting_pot_address")
    if not isinstance(pot, str) or not pot or pot == company_address:
        raise UnsafeGenesis("real on-chain vesting pot account required")
    if balances_map.get(pot) != GENESIS_LOCKED:
        raise UnsafeGenesis("vested balance is not held in verifiable pot")
    # The upstream vesting pallet requires a pot existential-deposit buffer.
    # That buffer would create extra initial issuance if 3M liquid and 7M
    # fully locked are both preserved. The production team MUST redesign
    # pot funding/ED accounting before accepting the independent genesis.
    # This is a deliberately fail-closed rule, not a zero-ED recommendation.
    ed = manifest.get("vesting_pot_existential_deposit_units")
    if not isinstance(ed, int) or isinstance(ed, bool) or ed != 0:
        raise UnsafeGenesis("STOP: vesting pot existential-deposit funding unresolved; do not mint above 10M")
    return {"genesis_issued_units":total_issued,"company_liquid_units":GENESIS_LIQUID,"locked_units":locked}
