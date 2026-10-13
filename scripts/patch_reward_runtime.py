#!/usr/bin/env python3
"""Patch the Quantus mining-rewards FRAME pallet with DVN accounting.

DEVELOPMENT INTEGRATION ONLY. Requires complete 8-decimal ZK/prover migration,
genesis and cross-pallet tests before any production use.
"""
from pathlib import Path
import argparse
try:
    from scripts.generate_emission_table import generate
except ModuleNotFoundError:
    # Supports direct execution: python3 scripts/patch_reward_runtime.py upstream
    from generate_emission_table import generate

PAYOUT_CODE = """\
\t\tfn on_finalize(block_number: BlockNumberFor<T>) {
\t\t\t// Subsidy issuance and burned transaction-fee reissue are distinct.
\t\t\t// The pending subsidy is reserved against the 90M mining budget,
\t\t\t// including credits deferred for a missing author or a mint failure.
\t\t\tlet fees = <CollectedFees<T>>::take();
\t\t\tlet pending_before = <PendingSubsidy<T>>::get();
\t\t\tlet already_mined = <MinedSubsidy<T>>::get();
\t\t\tlet budget = T::MiningCap::get()
\t\t\t\t.saturating_sub(already_mined)
\t\t\t\t.saturating_sub(pending_before);
\t\t\tlet height: u32 = block_number.saturated_into();
\t\t\tlet epoch = height.saturating_sub(1) / super::devnira_emission::DVN_EPOCH_BLOCKS;
\t\t\tlet epoch_units: BalanceOf<T> =
\t\t\t\t(super::devnira_emission::dvn_epoch_reward(epoch) as u128).saturated_into();
\t\t\tlet subsidy = if height == 0 { BalanceOf::<T>::zero() } else {
\t\t\t\tcore::cmp::min(epoch_units, budget)
\t\t\t};
\t\t\tlet pending = pending_before.saturating_add(subsidy);
\t\t\t<PendingSubsidy<T>>::put(pending);
\t\t\tlet gross = fees.saturating_add(pending);
\t\t\tlet Some(miner) = Self::extract_miner_from_digest() else {
\t\t\t\t<CollectedFees<T>>::put(fees);
\t\t\t\tif !gross.is_zero() {
\t\t\t\t\tSelf::deposit_event(Event::PayoutDeferred { amount: gross });
\t\t\t\t}
\t\t\t\treturn;
\t\t\t};
\t\t\tlet (payout, _) = Self::quantize(gross);
\t\t\tif payout.is_zero() {
\t\t\t\t<CollectedFees<T>>::put(fees);
\t\t\t\treturn;
\t\t\t}
\t\t\t// Consume previously burned fees before newly issued subsidy.
\t\t\t// This matters when combined credits round to a single leaf quantum.
\t\t\tlet paid_fees = core::cmp::min(payout, fees);
\t\t\tlet paid_subsidy = payout.saturating_sub(paid_fees);
\t\t\tdebug_assert!(paid_subsidy <= pending);
\t\t\tmatch T::Currency::mint_into(&miner, payout) {
\t\t\t\tOk(_) => {
\t\t\t\t\t<CollectedFees<T>>::put(fees.saturating_sub(paid_fees));
\t\t\t\t\t<PendingSubsidy<T>>::put(pending.saturating_sub(paid_subsidy));
\t\t\t\t\t<MinedSubsidy<T>>::put(already_mined.saturating_add(paid_subsidy));
\t\t\t\t\tT::ProofRecorder::record_transfer_proof(
\t\t\t\t\t\tNone, T::MintingAccount::get(), miner.clone(), payout,
\t\t\t\t\t);
\t\t\t\t\tSelf::deposit_event(Event::MinerRewarded { miner, reward: payout });
\t\t\t\t},
\t\t\t\tErr(_) => {
\t\t\t\t\t<CollectedFees<T>>::put(fees);
\t\t\t\t\tSelf::deposit_event(Event::MinerMintFailed { miner, reward: payout });
\t\t\t\t},
\t\t\t}
\t\t}
"""

def patch(root: Path) -> None:
    path = root / "pallets/mining-rewards/src/lib.rs"
    s = path.read_text()
    if "pub mod devnira_emission;" in s:
        raise ValueError("Already applied DVN mining patch; refusing double patch")
    if "let total_reward = remaining_supply" not in s:
        raise ValueError("Upstream mining reward body changed; manual review required")
    s = s.replace("pub use weights::*;", "pub use weights::*;\npub mod devnira_emission;", 1)
    s = s.replace("use sp_runtime::traits::Saturating;", "use sp_runtime::traits::{Saturating, SaturatedConversion};", 1)
    needle = "\t#[pallet::config]\n\tpub trait Config"
    new_storage = (
        "\t/// Successfully minted NEW miner subsidies, excluding fee recycling.\n"
        "\t#[pallet::storage]\n"
        "\t#[pallet::getter(fn mined_subsidy)]\n"
        "\tpub type MinedSubsidy<T: Config> = StorageValue<_, BalanceOf<T>, ValueQuery>;\n\n"
        "\t/// Subsidies reserved but not yet minted due to quantum or deferred payout.\n"
        "\t#[pallet::storage]\n"
        "\t#[pallet::getter(fn pending_subsidy)]\n"
        "\tpub type PendingSubsidy<T: Config> = StorageValue<_, BalanceOf<T>, ValueQuery>;\n\n"
    )
    if s.count(needle) != 1:
        raise ValueError("Cannot find unique pallet Config insertion")
    s = s.replace(needle, new_storage + needle, 1)
    needle = "\t\t/// The maximum total supply of tokens\n"
    if s.count(needle) != 1:
        raise ValueError("Missing MaxSupply config")
    s = s.replace(needle, (
        "\t\t/// Mining-only new subsidy issuance cap (90 million DVN).\n"
        "\t\t#[pallet::constant]\n"
        "\t\ttype MiningCap: Get<BalanceOf<Self>>;\n\n"
    ) + needle, 1)
    start = s.index("\t\tfn on_finalize(")
    end = s.index("\n\t}\n\n\timpl<T: Config> Pallet<T>", start)
    prior = s[start:end]
    if "let total_reward = remaining_supply" not in prior or "Self::mint_reward" not in prior:
        raise ValueError("Unexpected upstream on_finalize shape")
    s = s[:start] + PAYOUT_CODE.rstrip() + s[end:]
    path.write_text(s)
    (root / "pallets/mining-rewards/src/devnira_emission.rs").write_text(generate())
    configs = root / "runtime/src/configs/mod.rs"
    cfg = configs.read_text()
    needle = "\ttype MaxSupply = ConstU128<{ MAX_SUPPLY }>;"
    if cfg.count(needle) != 1:
        raise ValueError("Missing unique runtime mining cap insertion")
    cfg = cfg.replace(needle, needle + "\n\ttype MiningCap = ConstU128<{ 90_000_000 * UNIT }>;", 1)
    configs.write_text(cfg)
    print("Patched FRAME mining rewards for separate subsidy/fee accounting.")
    print("NOT VERIFIED: upstream mock tests and 8-decimal ZK circuit still need migration.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("upstream_root", type=Path)
    patch(ap.parse_args().upstream_root)
