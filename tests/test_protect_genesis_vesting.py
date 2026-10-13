import tempfile
import unittest
from pathlib import Path
from scripts.protect_genesis_vesting import patch

class ProtectGenesisVestingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        file = self.root / "pallets/vesting/src/lib.rs"
        file.parent.mkdir(parents=True)
        file.write_text(
            "\t#[pallet::event]\n"
            "\t\t\tNextScheduleId::<T>::put(self.schedules.len() as u64);\n"
            "\t\tpub fn end_schedule(origin: OriginFor<T>, schedule_id: u64) -> DispatchResult {\n"
            "\t\t\tensure!(new_beneficiary != Self::pot_account_id(), Error::<T>::InvalidBeneficiary);\n"
        )

    def test_protection_injected(self):
        patch(self.root)
        source = (self.root / "pallets/vesting/src/lib.rs").read_text()
        self.assertIn("ImmutableGenesisScheduleCount::<T>::put(self.schedules.len() as u64)", source)
        self.assertEqual(source.count('DispatchError::Other("ImmutableGenesisGrant")'), 2)
        self.assertIn("pub type ImmutableGenesisScheduleCount", source)

    def test_rejects_double_patch(self):
        patch(self.root)
        with self.assertRaisesRegex(ValueError, "already applied"):
            patch(self.root)

    def test_refuses_changed_upstream(self):
        file = self.root / "pallets/vesting/src/lib.rs"
        file.write_text(file.read_text().replace("NextScheduleId::<T>::put", "NewScheduleId::<T>::put"))
        with self.assertRaisesRegex(ValueError, "Upstream genesis schedule insertion changed"):
            patch(self.root)

if __name__ == "__main__":
    unittest.main()
