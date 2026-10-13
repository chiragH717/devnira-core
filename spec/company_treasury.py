"""Strict single-company DEVNIRA treasury genesis allocation plan.

This is NOT the on-chain genesis or an address generator. Only a public,
independently verified native DVN account can replace the pending address.
"""
from dataclasses import dataclass
from datetime import datetime
from spec.genesis_allocations import Beneficiary, INSTANT_BUDGET, VESTED_BUDGET
from spec.genesis_manifest import build_manifest

class UnverifiedCompanyAddress(ValueError):
    pass

@dataclass(frozen=True)
class CompanyTreasury:
    public_address: str
    address_verified: bool = False

    def beneficiary(self) -> Beneficiary:
        if not self.address_verified:
            raise UnverifiedCompanyAddress("company DVN public wallet address must be verified")
        if not self.public_address or not self.public_address.strip():
            raise UnverifiedCompanyAddress("company DVN public wallet address is missing")
        if self.public_address != self.public_address.strip():
            raise UnverifiedCompanyAddress("company wallet address contains whitespace")
        # A string match is not an SS58 verifier: the caller must independently
        # check network prefix, checksum, account key and wallet ownership.
        return Beneficiary(self.public_address, INSTANT_BUDGET, VESTED_BUDGET)

def company_genesis_manifest(genesis_utc: datetime, treasury: CompanyTreasury) -> dict:
    result = build_manifest(genesis_utc, [treasury.beneficiary()])
    if len(result["beneficiaries"]) != 1 or len(result["monthly_unlocks"]) != 12:
        raise AssertionError("company treasury policy violated")
    result["beneficiary_policy"] = "single_company_treasury"
    result["company_address_verification"] = "externally_asserted_not_validated_by_this_script"
    result["company_spendable_at_genesis_units"] = INSTANT_BUDGET
    result["company_total_locked_at_genesis_units"] = VESTED_BUDGET
    result["production_genesis"] = False
    return result
