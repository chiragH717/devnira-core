#!/usr/bin/env python3
"""Add a strict DVN 8-decimal amount codec to the upstream ZK-tree pallet.

Opt-in compatibility prototype: DOES NOT replace leaf hashing, prover or verifier.
It is unsafe to enable the V2 format on-chain until all proof circuits are migrated.
"""
from pathlib import Path
import argparse

MODULE = r'''//! DEVNIRA native DVN amount V2: one canonical Goldilocks felt.
//! Prototype only. No V1/V2 leaf-hash or verifier mixing is permitted.
pub const DVN_UNIT: u64 = 100_000_000;
pub const DVN_MAX_NATIVE_UNITS: u64 = 100_000_000 * DVN_UNIT;
pub const GOLDILOCKS_PRIME: u64 = 0xFFFF_FFFF_0000_0001;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AmountCodecError {
    AboveNativeSupply,
    NonCanonicalField,
}

pub const fn encode_native(amount: u64) -> Result<[u8; 8], AmountCodecError> {
    if amount > DVN_MAX_NATIVE_UNITS {
        return Err(AmountCodecError::AboveNativeSupply);
    }
    Ok(amount.to_le_bytes())
}

pub const fn decode_native(bytes: [u8; 8]) -> Result<u64, AmountCodecError> {
    let amount = u64::from_le_bytes(bytes);
    if amount >= GOLDILOCKS_PRIME {
        return Err(AmountCodecError::NonCanonicalField);
    }
    if amount > DVN_MAX_NATIVE_UNITS {
        return Err(AmountCodecError::AboveNativeSupply);
    }
    Ok(amount)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn dvn_native_felt_roundtrip() {
        for amount in [0, 1, DVN_UNIT, 5 * DVN_UNIT, 58_333_333_333_333, DVN_MAX_NATIVE_UNITS] {
            assert_eq!(decode_native(encode_native(amount).unwrap()), Ok(amount));
        }
    }

    #[test]
    fn dvn_rejects_out_of_range_amounts() {
        assert_eq!(encode_native(DVN_MAX_NATIVE_UNITS + 1), Err(AmountCodecError::AboveNativeSupply));
        assert_eq!(decode_native((DVN_MAX_NATIVE_UNITS + 1).to_le_bytes()), Err(AmountCodecError::AboveNativeSupply));
        assert_eq!(decode_native(GOLDILOCKS_PRIME.to_le_bytes()), Err(AmountCodecError::NonCanonicalField));
    }
}
'''

def patch(root: Path) -> None:
    module = root / "pallets/zk-tree/src/devnira_amount.rs"
    lib = root / "pallets/zk-tree/src/lib.rs"
    source = lib.read_text()
    if module.exists() or "pub mod devnira_amount;" in source:
        raise ValueError("DEVNIRA ZK amount prototype already applied")
    if "#![cfg_attr(not(feature = \"std\"), no_std)]" not in source:
        raise ValueError("ZK-tree pallet upstream changed; manual review required")
    module.write_text(MODULE)
    lib.write_text(source + "\n// Prototype codec, not active leaf format or verifier.\npub mod devnira_amount;\n")
    print("Added strict DVN native amount codec to actual ZK-tree pallet (inactive prototype).")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream_root", type=Path)
    patch(parser.parse_args().upstream_root)
