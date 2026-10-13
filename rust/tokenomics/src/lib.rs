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

/// Consensus budget accounting reference (NOT a FRAME storage implementation).
///
/// Pending block subsidies reserve mining allocation immediately, even if no
/// author is present or minting fails. Recycled transaction fees never count
/// toward newly-issued DVN. Do not use total token issuance as a substitute
/// for this accounting, since fees may be temporarily burned.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct MiningLedger {
    pub minted_subsidy: u128,
    pub pending_subsidy: u128,
    pub pending_fees: u128,
}

impl MiningLedger {
    pub fn reserve_block(&mut self, height: u64) -> Result<u128, &'static str> {
        let used = self.minted_subsidy.checked_add(self.pending_subsidy)
            .ok_or("mined supply overflow")?;
        let emission = block_subsidy(height, used)?;
        self.pending_subsidy = self.pending_subsidy.checked_add(emission)
            .ok_or("pending subsidy overflow")?;
        Ok(emission)
    }

    pub fn collect_fees(&mut self, fees: u128) -> Result<(), &'static str> {
        self.pending_fees = self.pending_fees.checked_add(fees)
            .ok_or("fee overflow")?;
        Ok(())
    }

    /// Mark successfully minted subsidy, never fees, as new issuance.
    /// For exact ZK-quantized payouts use separate fee/subsidy subledgers.
    pub fn settle_subsidy(&mut self, amount: u128) -> Result<(), &'static str> {
        if amount > self.pending_subsidy { return Err("exceeds reserved subsidy"); }
        self.pending_subsidy -= amount;
        self.minted_subsidy = self.minted_subsidy.checked_add(amount)
            .ok_or("minted subsidy overflow")?;
        Ok(())
    }

    pub fn settle_fees(&mut self, amount: u128) -> Result<(), &'static str> {
        if amount > self.pending_fees { return Err("exceeds collected fees"); }
        self.pending_fees -= amount;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test] fn first_epoch() { assert_eq!(block_subsidy(1, 0), Ok(500_000_000)); }
    #[test] fn second_epoch() { assert_eq!(block_subsidy(50_001, 0), Ok(498_750_000)); }
    #[test] fn later_epochs() { assert_eq!(epoch_subsidy(2), 497_503_125); assert_eq!(epoch_subsidy(10_000), 1); }
    #[test] fn cap() { assert_eq!(block_subsidy(1, MINING_CAP-2), Ok(2)); assert_eq!(block_subsidy(1, MINING_CAP), Ok(0)); }
    #[test] fn invalid() { assert!(block_subsidy(0, 0).is_err()); assert!(block_subsidy(1, MAX_SUPPLY).is_err()); }
    #[test] fn fee_recycling_never_consumes_mining_budget() {
        let mut ledger = MiningLedger::default();
        ledger.collect_fees(8_000_000_000).unwrap();
        assert_eq!(ledger.reserve_block(1), INITIAL_SUBSIDY);
        ledger.settle_fees(8_000_000_000).unwrap();
        assert_eq!(ledger.minted_subsidy, 0);
        ledger.settle_subsidy(INITIAL_SUBSIDY).unwrap();
        assert_eq!(ledger.minted_subsidy, INITIAL_SUBSIDY);
        assert_eq!(ledger.pending_subsidy, 0);
    }
    #[test] fn pending_subsidy_prevents_overallocation() {
        let mut ledger = MiningLedger {
            minted_subsidy: MINING_CAP - 10, pending_subsidy: 8, pending_fees: 0,
        };
        assert_eq!(ledger.reserve_block(1), Ok(2));
        assert_eq!(ledger.reserve_block(2), Ok(0));
        assert!(ledger.settle_subsidy(11).is_err());
    }
    #[test] fn allocations() { assert_eq!(TEAM_ALLOCATION + MINING_CAP, MAX_SUPPLY); }
}
