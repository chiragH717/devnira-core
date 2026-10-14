import unittest
from scripts.project_status import status

class ProjectStatusTests(unittest.TestCase):
    def test_approved_economics_and_single_company_treasury(self):
        report = status()
        self.assertEqual(report["approved_supply"]["max_DVN"], 100_000_000)
        self.assertEqual(report["approved_supply"]["mined_DVN"], 90_000_000)
        self.assertEqual(report["approved_supply"]["liquid_company_DVN"], 3_000_000)
        self.assertEqual(report["approved_supply"]["twelve_month_company_locked_DVN"], 7_000_000)
        self.assertTrue(report["economics_configuration_valid"])

    def test_public_development_prototypes_never_claim_live_services(self):
        report = status()
        self.assertTrue(report["website"]["frontend_in_core_repo"])
        self.assertTrue(report["block_explorer"]["local_raw_block_lookup_source"])
        self.assertTrue(report["mining_pool"]["offline_accounting_preview_only"])
        self.assertFalse(report["website"]["verified_public_deployment"])
        self.assertFalse(report["block_explorer"]["public_explorer_deployment"])
        self.assertFalse(report["mining_pool"]["validated_shares_and_payouts"])

    def test_cannot_misstate_development_candidate_as_mainnet(self):
        report = status()
        self.assertEqual(report["network"], "NOT MAINNET READY")
        self.assertTrue(any("Poseidon2" in b for b in report["known_blockers"]))
        self.assertTrue(any("existential-deposit" in b for b in report["known_blockers"]))
        self.assertTrue(any("public address" in b for b in report["known_blockers"]))
        self.assertTrue(any("NVIDIA" in b for b in report["known_blockers"]))

if __name__ == "__main__":
    unittest.main()
