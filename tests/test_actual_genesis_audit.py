import unittest
from copy import deepcopy
from datetime import datetime, timezone
from spec.audit_actual_genesis import audit_candidate, UnsafeGenesis, GENESIS_LOCKED, GENESIS_LIQUID
from spec.genesis_manifest import build_manifest
from spec.genesis_allocations import Beneficiary

ADDR = "TEST_PUBLIC_ACCOUNT_NOT_REAL"
POT = "TEST_VESTING_POT_NOT_REAL"

def fixture():
    manifest = build_manifest(datetime(2027, 1, 31, 12, tzinfo=timezone.utc),
                              [Beneficiary(ADDR, GENESIS_LIQUID, GENESIS_LOCKED)])
    manifest["production_genesis"] = True
    manifest["company_address_verified"] = True
    manifest["onchain_vesting_pot_address"] = POT
    manifest["vesting_pot_existential_deposit_units"] = 0
    spec = {"id":"devnira-mainnet-v1","chainType":"Live",
            "properties":{"tokenDecimals":8,"tokenSymbol":"DVN","ss58Format":190},
            "bootNodes":[], "genesis":{"runtime":{
                "balances":{"balances":[[ADDR,GENESIS_LIQUID],[POT,GENESIS_LOCKED]]},
                "vesting":{"anchorToFirstTimestamp":False,
                           "schedules":deepcopy(manifest["runtime_vesting_schedules_absolute_ms"])}
            }}}
    return spec, manifest

class ActualGenesisAuditTests(unittest.TestCase):
    def test_exact_offline_shape_only(self):
        spec, manifest = fixture()
        report = audit_candidate(spec, ADDR, manifest)
        self.assertEqual(report["genesis_issued_units"], 10_000_000 * 100_000_000)

    def test_offchain_manifest_cannot_qualify(self):
        spec, manifest = fixture()
        manifest["production_genesis"] = False
        with self.assertRaisesRegex(UnsafeGenesis, "off-chain"):
            audit_candidate(spec, ADDR, manifest)

    def test_upstream_dev_chain_cannot_qualify(self):
        spec, manifest = fixture()
        spec["id"] = "dev"
        with self.assertRaisesRegex(UnsafeGenesis, "independent"):
            audit_candidate(spec, ADDR, manifest)

    def test_extra_issuance_rejected(self):
        spec, manifest = fixture()
        spec["genesis"]["runtime"]["balances"]["balances"].append(["third-party",1])
        with self.assertRaisesRegex(UnsafeGenesis, "exactly 10M"):
            audit_candidate(spec, ADDR, manifest)

    def test_mismatched_month_or_payout_rejected(self):
        spec, manifest = fixture()
        spec["genesis"]["runtime"]["vesting"]["schedules"][0][4] += 1
        with self.assertRaisesRegex(UnsafeGenesis, "differ"):
            audit_candidate(spec, ADDR, manifest)

    def test_pot_existential_deposit_is_consensus_blocker(self):
        spec, manifest = fixture()
        manifest["vesting_pot_existential_deposit_units"] = 100_000
        with self.assertRaisesRegex(UnsafeGenesis, "existential-deposit"):
            audit_candidate(spec, ADDR, manifest)

    def test_unknown_company_address_rejected(self):
        spec, manifest = fixture()
        with self.assertRaisesRegex(UnsafeGenesis, "exactly 3M"):
            audit_candidate(spec, "another-public-account", manifest)

if __name__ == "__main__":
    unittest.main()
