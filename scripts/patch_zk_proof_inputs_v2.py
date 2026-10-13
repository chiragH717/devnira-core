#!/usr/bin/env python3
"""Inject V2 base-unit amount model in real upstream qp-wormhole-inputs crate.

This adds a versioned module without altering V1 proof parsing or circuits.
Production must migrate leaf circuit, aggregator and verifier to V2 as a unit.
"""
import argparse
from pathlib import Path

V2_MODULE = r'''//! DEVNIRA native amount V2 (pre-production).
//! Canonical single Goldilocks field element, 8 DVN decimal places.
//! This codec is not connected to any V1 proof public-input parser.
//! The new aggregation circuits and verifier MUST use this exact format.
pub const DVN_UNIT: u64 = 100_000_000;
pub const DVN_NATIVE_MAX_UNITS: u64 = 100_000_000 * DVN_UNIT;
pub const GOLDILOCKS_ORDER: u64 = 0xFFFF_FFFF_0000_0001;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum DvnAmountError {
    ExceedsNativeCap,
    NonCanonicalFelt,
    ConservationViolation,
    Overflow,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct NativeDvnAmounts {
    /// Exact authenticated leaf amount in 1e-8 DVN units.
    pub input: u64,
    /// Exact first exit amount in 1e-8 DVN units.
    pub output_1: u64,
    /// Exact change amount in 1e-8 DVN units.
    pub output_2: u64,
}

impl NativeDvnAmounts {
    pub fn try_new(input: u64, output_1: u64, output_2: u64) -> Result<Self, DvnAmountError> {
        check_native(input)?;
        check_native(output_1)?;
        check_native(output_2)?;
        let output_sum = output_1.checked_add(output_2).ok_or(DvnAmountError::Overflow)?;
        if output_sum > input {
            return Err(DvnAmountError::ConservationViolation);
        }
        Ok(Self { input, output_1, output_2 })
    }
    /// Remaining amount for fees and any permitted burn; actual fee rule is
    /// a *separate circuit constraint* and must be checked in the circuit.
    pub fn remainder(&self) -> u64 {
        self.input - self.output_1 - self.output_2
    }
    pub fn encode_public_inputs(&self) -> [u64; 3] {
        [self.input, self.output_1, self.output_2]
    }
    pub fn parse_public_inputs(felts: [u64; 3]) -> Result<Self, DvnAmountError> {
        for felt in felts {
            if felt >= GOLDILOCKS_ORDER {
                return Err(DvnAmountError::NonCanonicalFelt);
            }
        }
        Self::try_new(felts[0], felts[1], felts[2])
    }
}

pub fn check_native(amount: u64) -> Result<(), DvnAmountError> {
    if amount >= GOLDILOCKS_ORDER {
        return Err(DvnAmountError::NonCanonicalFelt);
    }
    if amount > DVN_NATIVE_MAX_UNITS {
        return Err(DvnAmountError::ExceedsNativeCap);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn dvn_v2_accepts_exact_eight_decimal_base_units() {
        for amount in [0, 1, DVN_UNIT, 58_333_333_333_333, DVN_NATIVE_MAX_UNITS] {
            let amounts = NativeDvnAmounts::try_new(amount, amount, 0).unwrap();
            assert_eq!(NativeDvnAmounts::parse_public_inputs(amounts.encode_public_inputs()), Ok(amounts));
        }
    }
    #[test]
    fn dvn_v2_checks_value_conservation_without_u32_truncation() {
        let original = 10_000_000_000_000u64;
        let first = 5_000_000_000_001u64;
        let change = 4_999_999_999_998u64;
        let amounts = NativeDvnAmounts::try_new(original, first, change).unwrap();
        assert_eq!(amounts.remainder(), 1);
        assert_eq!(
            NativeDvnAmounts::try_new(original, first, change + 2),
            Err(DvnAmountError::ConservationViolation)
        );
    }
    #[test]
    fn dvn_v2_rejects_noncanonical_or_unissued_values() {
        assert_eq!(check_native(GOLDILOCKS_ORDER), Err(DvnAmountError::NonCanonicalFelt));
        assert_eq!(check_native(DVN_NATIVE_MAX_UNITS + 1), Err(DvnAmountError::ExceedsNativeCap));
        assert_eq!(
            NativeDvnAmounts::parse_public_inputs([GOLDILOCKS_ORDER, 0, 0]),
            Err(DvnAmountError::NonCanonicalFelt)
        );
    }
}
'''

def patch(source_root: Path) -> None:
    folder = source_root / "wormhole/inputs/src"
    lib = folder / "lib.rs"
    module = folder / "devnira_v2.rs"
    source = lib.read_text()
    if module.exists() or "pub mod devnira_v2;" in source:
        raise ValueError("DVN V2 proof input module already applied")
    if "pub struct PublicCircuitInputs" not in source or "pub input_amount: u32" not in source:
        raise ValueError("Unexpected upstream circuit input API: manual review required")
    module.write_text(V2_MODULE)
    lib.write_text(source + "\n// DVN V2 pre-production codec; V1 proof format is unchanged.\npub mod devnira_v2;\n")
    print("Added DVN V2 native amount input module to real wormhole proof source (inactive).")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    patch(parser.parse_args().source_root)
