#!/usr/bin/env python3
"""Harden upstream FRAME vesting: forbid admin early-end/retarget of genesis grants.

DEVNIRA development patch, to be applied to a pinned upstream checkout.
Normal post-genesis schedules still support original admin operations.
A runtime upgrade with unrestricted Root could replace this rule: governance
controls still need independent security review before mainnet.
"""
import argparse
from pathlib import Path

def patch(root: Path):
    path = root / "pallets/vesting/src/lib.rs"
    src = path.read_text()
    storage_anchor = "	#[pallet::event]"
    if src.count(storage_anchor) != 1 or "ImmutableGenesisScheduleCount" in src:
        raise ValueError("Upstream storage layout changed or patch already applied")
    storage = (
        "	/// Genesis founder grants are not cancellable or retargetable by administrators.\n"
        "	#[pallet::storage]\n"
        "	pub type ImmutableGenesisScheduleCount<T: Config> = StorageValue<_, u64, ValueQuery>;\n\n"
    )
    src = src.replace(storage_anchor, storage + storage_anchor, 1)
    count_anchor = "			NextScheduleId::<T>::put(self.schedules.len() as u64);"
    if src.count(count_anchor) != 1:
        raise ValueError("Upstream genesis schedule insertion changed")
    src = src.replace(count_anchor,
        count_anchor + "
			ImmutableGenesisScheduleCount::<T>::put(self.schedules.len() as u64);", 1)
    error_anchor = "		pub fn end_schedule(origin: OriginFor<T>, schedule_id: u64) -> DispatchResult {"
    if src.count(error_anchor) != 1:
        raise ValueError("end_schedule signature changed")
    src = src.replace(error_anchor, error_anchor +
        "
			ensure!(schedule_id >= ImmutableGenesisScheduleCount::<T>::get(), "
        "DispatchError::Other(\"ImmutableGenesisGrant\"));", 1)
    target_anchor = "			ensure!(new_beneficiary != Self::pot_account_id(), Error::<T>::InvalidBeneficiary);"
    if src.count(target_anchor) != 1:
        raise ValueError("retarget validation changed")
    src = src.replace(target_anchor,
        "			ensure!(schedule_id >= ImmutableGenesisScheduleCount::<T>::get(), "
        "DispatchError::Other(\"ImmutableGenesisGrant\"));
" + target_anchor, 1)
    path.write_text(src)
    print("Patched FRAME genesis schedule protection. Requires compilation and functional tests.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream_root", type=Path)
    patch(parser.parse_args().upstream_root)
