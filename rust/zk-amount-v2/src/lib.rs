#![no_std]
//! Reference encoding for native DVN amounts in one Goldilocks field element.
//! NOT the operational ZK circuit, runtime leaf hash, prover, or verifier.

pub const DVN_UNIT: u64 = 100_000_000;
pub const MAX_SUPPLY_UNITS: u64 = 100_000_000 * DVN_UNIT;
pub const GOLDILOCKS_PRIME: u64 = 0xFFFF_FFFF_0000_0001;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AmountEncodingError {
    AboveDvnSupply,
    NonCanonicalFieldElement,
}

/// Encode a native amount exactly; never truncate, quantize, or saturate.
pub const fn encode_native(amount_units: u64) -> Result<[u8; 8], AmountEncodingError> {
    if amount_units > MAX_SUPPLY_UNITS {
        return Err(AmountEncodingError::AboveDvnSupply);
    }
    Ok(amount_units.to_le_bytes())
}

/// Parse an eight-byte field element, rejecting out-of-range native token amounts.
pub const fn decode_native(encoded: [u8; 8]) -> Result<u64, AmountEncodingError> {
    let amount = u64::from_le_bytes(encoded);
    if amount >= GOLDILOCKS_PRIME {
        return Err(AmountEncodingError::NonCanonicalFieldElement);
    }
    if amount > MAX_SUPPLY_UNITS {
        return Err(AmountEncodingError::AboveDvnSupply);
    }
    Ok(amount)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn full_precision_roundtrip() {
        for amount in [0, 1, 5 * DVN_UNIT, 58_333_333_333_333, MAX_SUPPLY_UNITS] {
            assert_eq!(decode_native(encode_native(amount).unwrap()), Ok(amount));
        }
    }

    #[test]
    fn rejects_values_outside_native_range() {
        assert_eq!(encode_native(MAX_SUPPLY_UNITS + 1), Err(AmountEncodingError::AboveDvnSupply));
        assert_eq!(decode_native(GOLDILOCKS_PRIME.to_le_bytes()), Err(AmountEncodingError::NonCanonicalFieldElement));
        assert_eq!(decode_native(u64::MAX.to_le_bytes()), Err(AmountEncodingError::NonCanonicalFieldElement));
        assert_eq!(decode_native((MAX_SUPPLY_UNITS + 1).to_le_bytes()), Err(AmountEncodingError::AboveDvnSupply));
    }

    #[test]
    fn fits_in_goldilocks_felt() {
        assert!(MAX_SUPPLY_UNITS < GOLDILOCKS_PRIME);
    }
}
