#!/usr/bin/env python3
"""Apply DEVNIRA's *real* FRAME vesting-pot exact-funding consensus option.

The upstream pallet requires obligations + ED at genesis. DVN promises exactly
3M liquid + 7M locked and cannot issue an extra ED. Introduce an explicit
runtime-controlled exact-pot mode. Upstream development behavior remains the
default (false); eventual independent DVN runtime must opt in (true).

Exact mode pays the final grant with Expendable preservation so the sovereign
pot account can close at zero. Intermediate transfers cannot leave a positive
pot balance below ED. Native balance transfers and ZK proof recording retain
their original transactional coupling. This patch needs native/WASM testing,
full runtime integration, actual genesis and security review.
"""
from pathlib import Path
import argparse

def replace_once(src: str, old: str, new: str, label: str) -> str:
    if src.count(old) != 1:
        raise ValueError(f"Unexpected upstream {label}: count={src.count(old)}")
    return src.replace(old, new, 1)

def patch(root: Path) -> None:
    lib_file = root / "pallets/vesting/src/lib.rs"
    config_file = root / "runtime/src/configs/mod.rs"
    mock_file = root / "pallets/vesting/src/mock.rs"
    preset_file = root / "runtime/src/genesis_config_presets/mod.rs"
    lib = lib_file.read_text()
    configs = config_file.read_text()
    mock = mock_file.read_text()
    presets = preset_file.read_text()
    if "type ExactGenesisFunding:" in lib:
        raise ValueError("Already applied exact genesis vesting patch")

    lib = replace_once(lib,
        "\t\ttype Currency: Inspect<Self::AccountId> + Mutate<Self::AccountId>;",
        "\t\ttype Currency: Inspect<Self::AccountId> + Mutate<Self::AccountId>;\n\n"
        "\t\t/// Allow exactly the scheduled funds in the genesis vesting pot.\n"
        "\t\t/// The final payout may reap an empty pot; upstream chains stay Preserve.\n"
        "\t\ttype ExactGenesisFunding: Get<bool>;",
        "FRAME currency config")

    lib = replace_once(lib,
        "\t\t\tlet required = sum\n"
        "\t\t\t\t.checked_add(&ed)\n"
        "\t\t\t\t.expect(\"vesting genesis: obligations plus existential deposit overflow Balance\");",
        "\t\t\tlet required = if T::ExactGenesisFunding::get() {\n"
        "\t\t\t\tsum\n"
        "\t\t\t} else {\n"
        "\t\t\t\tsum.checked_add(&ed)\n"
        "\t\t\t\t\t.expect(\"vesting genesis: obligations plus existential deposit overflow Balance\")\n"
        "\t\t\t};",
        "vesting genesis pot funding")

    lib = replace_once(lib,
        "\t\t\tT::Currency::transfer(from, to, amount, Preservation::Preserve)?;",
        "\t\t\tlet preservation = if T::ExactGenesisFunding::get() &&\n"
        "\t\t\t\tfrom == &Self::pot_account_id() {\n"
        "\t\t\t\tlet after = T::Currency::total_balance(from)\n"
        "\t\t\t\t\t.checked_sub(&amount).ok_or(ArithmeticError::Underflow)?;\n"
        "\t\t\t\t// Never reap a partially funded pot and silently burn an\n"
        "\t\t\t\t// outstanding beneficiary's remaining entitlement.\n"
        "\t\t\t\tensure!(after.is_zero() || after >= T::Currency::minimum_balance(),\n"
        "\t\t\t\t\tError::<T>::PotUnderfunded);\n"
        "\t\t\t\tPreservation::Expendable\n"
        "\t\t\t} else {\n"
        "\t\t\t\tPreservation::Preserve\n"
        "\t\t\t};\n"
        "\t\t\tT::Currency::transfer(from, to, amount, preservation)?;",
        "transfer and proof recording")

    lib = replace_once(lib,
        "\t\t\tlet required = if has_schedules {\n"
        "\t\t\t\toutstanding\n"
        "\t\t\t\t\t.checked_add(&T::Currency::minimum_balance())\n"
        "\t\t\t\t\t.ok_or(sp_runtime::TryRuntimeError::Other(\"required pot balance overflows\"))?\n"
        "\t\t\t} else {\n"
        "\t\t\t\tZero::zero()\n"
        "\t\t\t};",
        "\t\t\tlet required = if has_schedules && !T::ExactGenesisFunding::get() {\n"
        "\t\t\t\toutstanding\n"
        "\t\t\t\t\t.checked_add(&T::Currency::minimum_balance())\n"
        "\t\t\t\t\t.ok_or(sp_runtime::TryRuntimeError::Other(\"required pot balance overflows\"))?\n"
        "\t\t\t} else {\n"
        "\t\t\t\toutstanding\n"
        "\t\t\t};",
        "vesting try_state")

    # Preserve existing live-upstream behavior in development and other presets;
    # a true production DVN runtime must explicitly opt in after ZK migration.
    configs = replace_once(configs,
        "impl pallet_vesting::Config for Runtime {\n\ttype Currency = Balances;",
        "impl pallet_vesting::Config for Runtime {\n"
        "\ttype Currency = Balances;\n"
        "\t// Upstream development genesis still pre-funds ED. Independent DVN\n"
        "\t// runtime must enable this only alongside exact-pot genesis funding.\n"
        "\ttype ExactGenesisFunding = frame_support::traits::ConstBool<false>;",
        "runtime vesting implementation")

    mock = replace_once(mock,
        "\tpub static ExistentialDeposit: Balance = DEFAULT_EXISTENTIAL_DEPOSIT;",
        "\tpub static ExistentialDeposit: Balance = DEFAULT_EXISTENTIAL_DEPOSIT;\n"
        "\tpub static ExactGenesisFunding: bool = false;",
        "mock dynamic ED setting")
    mock = replace_once(mock,
        "impl pallet_vesting::Config for Test {\n\ttype Currency = Balances;",
        "impl pallet_vesting::Config for Test {\n\ttype Currency = Balances;\n"
        "\ttype ExactGenesisFunding = ExactGenesisFunding;",
        "mock vesting implementation")
    mock = replace_once(mock,
        "new_test_ext_inner(schedules, sum + DEFAULT_EXISTENTIAL_DEPOSIT, true)",
        "new_test_ext_inner(schedules, sum + DEFAULT_EXISTENTIAL_DEPOSIT, true, false)",
        "anchored mock caller")
    mock = replace_once(mock,
        "new_test_ext_inner(schedules, pot_balance, false)",
        "new_test_ext_inner(schedules, pot_balance, false, false)",
        "regular mock caller")
    mock = replace_once(mock,
        "fn reset_thread_local_state() {\n\tExistentialDeposit::set(DEFAULT_EXISTENTIAL_DEPOSIT);",
        "fn reset_thread_local_state() {\n"
        "\tExistentialDeposit::set(DEFAULT_EXISTENTIAL_DEPOSIT);\n"
        "\tExactGenesisFunding::set(false);",
        "mock thread state reset")
    mock = replace_once(mock,
        "\tanchor_to_first_timestamp: bool,\n) -> sp_io::TestExternalities {\n"
        "\treset_thread_local_state();",
        "\tanchor_to_first_timestamp: bool,\n"
        "\texact_genesis_funding: bool,\n"
        ") -> sp_io::TestExternalities {\n"
        "\treset_thread_local_state();\n"
        "\tExactGenesisFunding::set(exact_genesis_funding);\n"
        "\tif exact_genesis_funding {\n"
        "\t\t// DVN V2 uses 1 native base unit per ZK amount quantum.\n"
        "\t\tPayoutQuantum::set(1);\n"
        "\t}",
        "mock genesis options")
    insertion = '''/// DEVNIRA exact-pot genesis fixture: 7M locked can be funded with exactly 7M
/// base-unit obligations, not 7M + ED. This is mock-only and never creates
/// the company's real public account or independent genesis.
pub fn new_test_ext_exact(schedules: Vec<ScheduleTuple>) -> sp_io::TestExternalities {
    let sum: u128 = schedules.iter().map(|(_, _, _, _, total)| total).sum();
    new_test_ext_inner(schedules, sum, false, true)
}

'''
    mock = replace_once(mock, "/// Like [`new_test_ext`], but genesis times are offsets",
                        insertion + "/// Like [`new_test_ext`], but genesis times are offsets",
                        "mock schedule fixture anchor")
    # The real runtime genesis builder must follow the pallet's exact-pot
    # funding option; otherwise a true V2 runtime would still add extra ED.
    presets = replace_once(presets,
        "\\tbalances.push((\\n\\t\\tpot_account,\\n"
        "\\t\\tvesting_total\\n"
        "\\t\\t\\t.checked_add(EXISTENTIAL_DEPOSIT)\\n"
        "\\t\\t\\t.expect(\\\"vesting pot endowment overflows u128\\\"),\\n"
        "\\t));",
        "\\t// Match genesis pot funding to the actual FRAME vesting policy.\\n"
        "\\tlet pot_funding = if <<crate::Runtime as pallet_vesting::Config>::ExactGenesisFunding\\n"
        "\\t\\tas frame_support::traits::Get<bool>>::get() {\\n"
        "\\t\\tvesting_total\\n"
        "\\t} else {\\n"
        "\\t\\tvesting_total.checked_add(EXISTENTIAL_DEPOSIT)\\n"
        "\\t\\t\\t.expect(\\\"vesting pot endowment overflows u128\\\")\\n"
        "\\t};\\n"
        "\\tbalances.push((pot_account, pot_funding));",
        "runtime genesis pot funding")

    # Validate ALL match anchors before changing any file.
    lib_file.write_text(lib)
    mock_file.write_text(mock)
    config_file.write_text(configs)
    preset_file.write_text(presets)
    print("Applied opt-in exact-pot FRAME vesting semantics with no extra genesis ED.")
    print("Development runtime remains false. Production DVN activation and tests still required.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream_root", type=Path)
    patch(parser.parse_args().upstream_root)
