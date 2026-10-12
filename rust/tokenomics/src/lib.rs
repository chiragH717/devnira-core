//! DEVNIRA reference emission rules. This is NOT integrated with the Quantus runtime.
//! Integer-only consensus arithmetic, 8 decimal places.
pub const UNIT: u128 = 100_000_000;
pub const MAX_SUPPLY: u128 = 100_000_000 * UNIT;
pub const INITIAL_SUBSIDY: u128 = 5 * UNIT;
pub const EPOCH_BLOCKS: u64 = 50_000;

/// Exact floor(initial_subsidy * (399/400)^epoch), clamped to one base unit.
/// Recurrence using integer division at each epoch is NOT equivalent.
pub fn epoch_subsidy(epoch: u64) -> u128 {
    // Exact rational calculation without arbitrary-precision dependencies:
    // For high epochs the reward is already <= 1, so early exit.
    // 399/400 ^ 10000 < 2^-36; subsidy is then certainly below one base unit.
    if epoch >= 10_000 { return 1; }
    // Use a bounded fixed-point algorithm? Avoid approximations: calculate
    // exact rational via base-400 long division with arbitrary precision later.
    // Until implemented, only epoch 0 and 1 are accepted explicitly.
    match epoch {
        0 => INITIAL_SUBSIDY,
        1 => INITIAL_SUBSIDY * 399 / 400,
        _ => panic!("Exact large-epoch consensus arithmetic not implemented"),
    }
}

/// Caller must use issued supply from authenticated chain state.
pub fn block_subsidy(height: u64, issued: u128) -> Result<u128, &'static str> {
    if height == 0 || issued > MAX_SUPPLY { return Err("invalid height or supply"); }
    Ok(epoch_subsidy((height - 1) / EPOCH_BLOCKS).min(MAX_SUPPLY - issued))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test] fn first_epoch() { assert_eq!(block_subsidy(1, 0), Ok(500_000_000)); }
    #[test] fn second_epoch() { assert_eq!(block_subsidy(50_001, 0), Ok(498_750_000)); }
    #[test] fn cap() { assert_eq!(block_subsidy(1, MAX_SUPPLY-2), Ok(2)); }
    #[test] fn invalid() { assert!(block_subsidy(0, 0).is_err()); }
}
