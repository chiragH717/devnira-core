import tempfile
import unittest
from pathlib import Path

from scripts.patch_reward_runtime import patch


class RewardRuntimePatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        pallet = self.root / "pallets/mining-rewards/src"
        pallet.mkdir(parents=True)
        runtime = self.root / "runtime/src/configs"
        runtime.mkdir(parents=True)
        (pallet / "lib.rs").write_text(
            "pub use weights::*;\n"
            "use sp_runtime::traits::Saturating;\n"
            "#[frame_support::pallet]\n"
            "pub mod pallet {\n"
            "\t#[pallet::config]\n"
            "\tpub trait Config {\n"
            "\t\t/// The maximum total supply of tokens\n"
            "\t}\n"
            "\timpl<T: Config> Hooks<BlockNumberFor<T>> for Pallet<T> {\n"
            "\t\tfn on_finalize(_block_number: BlockNumberFor<T>) {\n"
            "\t\t\tlet total_reward = remaining_supply.checked_div(&emission_divisor);\n"
            "\t\t\tSelf::mint_reward(&miner, total_reward);\n"
            "\t\t}\n"
            "\t}\n\n"
            "\timpl<T: Config> Pallet<T> {\n\t}\n}\n"
        )
        (runtime / "mod.rs").write_text("\ttype MaxSupply = ConstU128<{ MAX_SUPPLY }>;\n")

    def test_patches_real_runtime_files(self):
        patch(self.root)
        reward = (self.root / "pallets/mining-rewards/src/lib.rs").read_text()
        config = (self.root / "runtime/src/configs/mod.rs").read_text()
        emission = (self.root / "pallets/mining-rewards/src/devnira_emission.rs").read_text()
        self.assertIn("pub type MinedSubsidy", reward)
        self.assertIn("pub type PendingSubsidy", reward)
        self.assertIn("type MiningCap", config)
        self.assertIn("DVN_REWARDS", emission)
        self.assertNotIn("let total_reward = remaining_supply", reward)

    def test_refuses_double_patch(self):
        patch(self.root)
        with self.assertRaisesRegex(ValueError, "Already applied"):
            patch(self.root)

    def test_fails_closed_when_upstream_changes(self):
        pallet = self.root / "pallets/mining-rewards/src/lib.rs"
        pallet.write_text(pallet.read_text().replace(
            "let total_reward = remaining_supply", "let total_reward = new_formula"
        ))
        with self.assertRaisesRegex(ValueError, "Upstream mining reward body changed"):
            patch(self.root)


if __name__ == "__main__":
    unittest.main()
