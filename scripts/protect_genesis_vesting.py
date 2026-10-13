#!/usr/bin/env python3
"""Protect on-chain genesis vesting grants from admin cancellation/retarget.

Development patch, NOT a production-ready runtime. Native/WASM tests required.
"""
import argparse
from pathlib import Path


def patch(root: Path) -> None:
    path = root / "pallets/vesting/src/lib.rs"
    src = path.read_text()
    storage_anchor = "\t#[pallet::event]"
    if src.count(storage_anchor) != 1 or "ImmutableGenesisScheduleCount" in src:
        raise ValueError("Upstream storage layout changed or patch already applied")
    storage = (
        "\t/// Genesis grants are not cancellable or retargetable by administrators.\n"
        "\t#[pallet::storage]\n"
        "\tpub type ImmutableGenesisScheduleCount<T: Config> = StorageValue<_, u64, ValueQuery>;\n\n"
    )
    src = src.replace(storage_anchor, storage + storage_anchor, 1)
    count_anchor = "\t\t\tNextScheduleId::<T>::put(self.schedules.len() as u64);"
    if src.count(count_anchor) != 1:
        raise ValueError("Upstream genesis schedule insertion changed")
    src = src.replace(
        count_anchor,
        count_anchor + "\n\t\t\tImmutableGenesisScheduleCount::<T>::put(self.schedules.len() as u64);",
        1,
    )
    end_anchor = "\t\tpub fn end_schedule(origin: OriginFor<T>, schedule_id: u64) -> DispatchResult {"
    if src.count(end_anchor) != 1:
        raise ValueError("end_schedule signature changed")
    src = src.replace(
        end_anchor,
        end_anchor + "\n\t\t\tensure!(schedule_id >= ImmutableGenesisScheduleCount::<T>::get(), "
        'DispatchError::Other("ImmutableGenesisGrant"));',
        1,
    )
    retarget_anchor = "\t\t\tensure!(new_beneficiary != Self::pot_account_id(), Error::<T>::InvalidBeneficiary);"
    if src.count(retarget_anchor) != 1:
        raise ValueError("retarget validation changed")
    src = src.replace(
        retarget_anchor,
        "\t\t\tensure!(schedule_id >= ImmutableGenesisScheduleCount::<T>::get(), "
        'DispatchError::Other("ImmutableGenesisGrant"));\n' + retarget_anchor,
        1,
    )
    path.write_text(src)
    print("Patched FRAME genesis vesting grant protection; compile/test required.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream_root", type=Path)
    patch(parser.parse_args().upstream_root)
