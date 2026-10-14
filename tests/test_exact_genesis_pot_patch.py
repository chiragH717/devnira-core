import tempfile
import unittest
from pathlib import Path

from scripts.patch_exact_genesis_vesting import patch, replace_once
from scripts.test_exact_genesis_vesting import generate_tests

LIB = (
    "\t\ttype Currency: Inspect<Self::AccountId> + Mutate<Self::AccountId>;\n"
    "\t\t\tlet required = sum\n"
    "\t\t\t\t.checked_add(&ed)\n"
    "\t\t\t\t.expect(\"vesting genesis: obligations plus existential deposit overflow Balance\");\n"
    "\t\t\tT::Currency::transfer(from, to, amount, Preservation::Preserve)?;\n"
    "\t\t\tlet required = if has_schedules {\n"
    "\t\t\t\toutstanding\n"
    "\t\t\t\t\t.checked_add(&T::Currency::minimum_balance())\n"
    "\t\t\t\t\t.ok_or(sp_runtime::TryRuntimeError::Other(\"required pot balance overflows\"))?\n"
    "\t\t\t} else {\n"
    "\t\t\t\tZero::zero()\n"
    "\t\t\t};\n"
)
MOCK = (
    "\tpub static ExistentialDeposit: Balance = DEFAULT_EXISTENTIAL_DEPOSIT;\n"
    "impl pallet_vesting::Config for Test {\n\ttype Currency = Balances;\n"
    "new_test_ext_inner(schedules, sum + DEFAULT_EXISTENTIAL_DEPOSIT, true)\n"
    "new_test_ext_inner(schedules, pot_balance, false)\n"
    "fn reset_thread_local_state() {\n\tExistentialDeposit::set(DEFAULT_EXISTENTIAL_DEPOSIT);\n"
    "\tanchor_to_first_timestamp: bool,\n) -> sp_io::TestExternalities {\n"
    "\treset_thread_local_state();\n"
    "/// Like [`new_test_ext`], but genesis times are offsets\n"
)

class ExactGenesisPotPatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.files = {
            "pallets/vesting/src/lib.rs": LIB,
            "runtime/src/configs/mod.rs": "impl pallet_vesting::Config for Runtime {\n\ttype Currency = Balances;",
            "pallets/vesting/src/mock.rs": MOCK,
        }
        for relative, source in self.files.items():
            dest = self.root / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(source)

    def test_genuine_runtime_configuration_and_conservation_guards(self):
        patch(self.root)
        pallet = (self.root / "pallets/vesting/src/lib.rs").read_text()
        mock = (self.root / "pallets/vesting/src/mock.rs").read_text()
        configs = (self.root / "runtime/src/configs/mod.rs").read_text()
        self.assertIn("type ExactGenesisFunding: Get<bool>", pallet)
        self.assertIn("Preservation::Expendable", pallet)
        self.assertIn("after.is_zero() || after >= T::Currency::minimum_balance()", pallet)
        self.assertIn("let required = if T::ExactGenesisFunding::get()", pallet)
        self.assertIn("outstanding\n", pallet)
        self.assertIn("new_test_ext_exact", mock)
        self.assertIn("PayoutQuantum::set(1)", mock)
        self.assertIn("ConstBool<false>", configs, "Upstream dev preset must remain unchanged")

    def test_rejects_second_application(self):
        patch(self.root)
        with self.assertRaisesRegex(ValueError, "Already applied"):
            patch(self.root)

    def test_rejects_upstream_drift_without_partial_mutation(self):
        path = self.root / "pallets/vesting/src/lib.rs"
        path.write_text(LIB.replace("Preservation::Preserve", "Preservation::Fortitude"))
        with self.assertRaisesRegex(ValueError, "transfer and proof"):
            patch(self.root)
        self.assertEqual(path.read_text(), LIB.replace("Preservation::Preserve", "Preservation::Fortitude"))
        self.assertEqual((self.root / "pallets/vesting/src/mock.rs").read_text(), MOCK)

    def test_conservation_test_generates_all_twelve_calendar_boundaries(self):
        body = generate_tests()
        self.assertIn("dvn_exact_pot_all_twelve_monthly_grants_mint_no_extra_ed", body)
        self.assertIn("dvn_exact_pot_prevents_premature_reaping_below_ed", body)
        self.assertIn("700_000_000_000_000", body)
        self.assertIn("Balances::total_issuance()", body)
        self.assertEqual(body.count("2027"), 0, "timestamps should be encoded as numeric milliseconds")
        self.assertEqual(body.count("u64"), 14)  # 12 Gregorian deadlines plus 2 explicit constants

if __name__ == "__main__":
    unittest.main()
