//! DEVNIRA reference emission arithmetic; NOT yet wired to the production runtime.
use num_bigint::BigUint;
use num_traits::ToPrimitive;

pub const UNIT: u128 = 100_000_000;
pub const MAX_SUPPLY: u128 = 100_000_000 * UNIT;
pub const TEAM_ALLOCATION: u128 = 10_000_000 * UNIT;
pub const MINING_CAP: u128 = MAX_SUPPLY - TEAM_ALLOCATION;
pub const INITIAL_SUBSIDY: u128 = 5 * UNIT;
pub const EPOCH_BLOCKS: u64 = 50_000;

/// Exact floor(500000000 * (399/400)^epoch), with 1-base-unit tail.
/// 10,000 epochs is a conservative cutoff: the rational reward is below one.
pub fn epoch_subsidy(epoch: u64) -> u128 {
    if epoch >= 10_000 { return 1; }
    let e = u32::try_from(epoch).expect("epoch bounded");
    let numerator = BigUint::from(INITIAL_SUBSIDY) * BigUint::from(399u32).pow(e);
    let denominator = BigUint::from(400u32).pow(e);
    (numerator / denominator).to_u128().expect("reward <= initial").max(1)
}

/// Issued represents mined DVN only, excluding the 10M DVN genesis allocation.
pub fn block_subsidy(height: u64, mined_issued: u128) -> Result<u128, &'static str> {
    if height == 0 || mined_issued > MINING_CAP { return Err("invalid height or mined supply"); }
    Ok(epoch_subsidy((height - 1) / EPOCH_BLOCKS).min(MINING_CAP - mined_issued))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test] fn first_epoch() { assert_eq!(block_subsidy(1, 0), Ok(500_000_000)); }
    #[test] fn second_epoch() { assert_eq!(block_subsidy(50_001, 0), Ok(498_750_000)); }
    #[test] fn later_epochs() { assert_eq!(epoch_subsidy(2), 497_503_125); assert_eq!(epoch_subsidy(10_000), 1); }
    #[test] fn cap() { assert_eq!(block_subsidy(1, MINING_CAP-2), Ok(2)); assert_eq!(block_subsidy(1, MINING_CAP), Ok(0)); }
    #[test] fn invalid() { assert!(block_subsidy(0, 0).is_err()); assert!(block_subsidy(1, MAX_SUPPLY).is_err()); }
    #[test] fn allocations() { assert_eq!(TEAM_ALLOCATION + MINING_CAP, MAX_SUPPLY); }
}
