#!/usr/bin/env python3
"""Add an opt-in full-precision DEVNIRA native leaf commitment to actual FRAME ZK tree.

The legacy V1 `hash_leaf` and on-chain state transition remain unchanged.
The new proof hash is reserved for coherent V2 runtime + prover + verifier activation.
Native DVN u64 amount up to 1e16 remains EXACT (no quantization or u32 cast).
"""
import argparse
from pathlib import Path

MARKER = "pub const DVN_NATIVE_MAX_BASE_UNITS_V2: u128 = 10_000_000_000_000_000;"

V2_HASH_FN = r'''
/// DEVNIRA V2 native maximal total supply expressed in eight-decimal base units.
pub const DVN_NATIVE_MAX_BASE_UNITS_V2: u128 = 10_000_000_000_000_000;

/// V2-only Poseidon leaf hash candidate. Inactive until on-chain/prover/verifier
/// activation is atomic. Unlike old hash_leaf, exact native amounts differing
/// by ONE 1e-8 DVN unit produce distinct commitments.
///
/// The felt layout is identical (4 account + 2 transfer count + 1 asset ID
/// + 1 amount), but the amount is a canonical u64 field element and never a
/// quantized u32. Reject oversupply and out-of-range assets, do not saturate.
pub fn hash_leaf_native_v2<T: Config>(
    leaf: &ZkLeaf<AccountIdOf<T>, T::AssetId, T::Balance>,
) -> Result<Hash256, &'static str> {
    use qp_poseidon_core::serialization::u64_to_felts;
    let native_amount: u128 = leaf.amount.into();
    if native_amount > DVN_NATIVE_MAX_BASE_UNITS_V2 {
        return Err("DVN V2 native leaf amount exceeds 100M supply");
    }
    let asset_id_u128: u128 = leaf.asset_id.into();
    let asset_id = u32::try_from(asset_id_u128)
        .map_err(|_| "DVN V2 asset ID is not a u32")?;
    let account_bytes = leaf.to.as_ref();
    if account_bytes.len() != 32 {
        return Err("DVN V2 requires an AccountId32");
    }
    if !account_bytes.chunks_exact(8).all(|chunk| {
        let limb: [u8; 8] = chunk.try_into().expect("chunks_exact(8)");
        u64::from_le_bytes(limb) < GOLDILOCKS_P
    }) {
        return Err("DVN V2 recipient is not canonical in Goldilocks encoding");
    }
    let mut felts = Vec::with_capacity(8);
    felts.extend(bytes_to_felts_compact_lossy(account_bytes));
    felts.extend(u64_to_felts(leaf.transfer_count));
    felts.extend(bytes_to_felts_compact_lossy(&(asset_id as u64).to_le_bytes()));
    felts.extend(bytes_to_felts_compact_lossy(&(native_amount as u64).to_le_bytes()));
    debug_assert_eq!(felts.len(), 8);
    Ok(qp_poseidon_core::hash_to_bytes(&felts))
}

'''
V2_TESTS = r'''
// BEGIN DEVNIRA V2 EXACT NATIVE LEAF TESTS
#[test]
fn dvn_native_v2_leaf_commits_every_eight_decimal_base_unit_exactly() {
    let a = amount_leaf(500_000_000);
    let b = amount_leaf(500_000_001);
    let hash_a = tree::hash_leaf_native_v2::<Test>(&a).unwrap();
    let hash_b = tree::hash_leaf_native_v2::<Test>(&b).unwrap();
    assert_ne!(hash_a, hash_b, "one base unit change must change V2 commitment");
    assert_ne!(
        tree::hash_leaf_native_v2::<Test>(&amount_leaf(0)).unwrap(),
        tree::hash_leaf_native_v2::<Test>(&amount_leaf(1)).unwrap(),
    );
}

#[test]
fn dvn_native_v2_leaf_accepts_100m_cap_but_rejects_oversupply() {
    let max = tree::DVN_NATIVE_MAX_BASE_UNITS_V2;
    assert!(tree::hash_leaf_native_v2::<Test>(&amount_leaf(max)).is_ok());
    assert_eq!(
        tree::hash_leaf_native_v2::<Test>(&amount_leaf(max + 1)),
        Err("DVN V2 native leaf amount exceeds 100M supply")
    );
    assert_eq!(
        tree::hash_leaf_native_v2::<Test>(&amount_leaf(u128::MAX)),
        Err("DVN V2 native leaf amount exceeds 100M supply")
    );
}
// END DEVNIRA V2 EXACT NATIVE LEAF TESTS
'''

def patch(root: Path) -> None:
    code_file = root/"pallets/zk-tree/src/tree.rs"
    tests_file = root/"pallets/zk-tree/src/tests.rs"
    code=code_file.read_text()
    tests=tests_file.read_text()
    anchor="/// Hash 4 child hashes into a parent node hash."
    if MARKER in code or "// BEGIN DEVNIRA V2 EXACT NATIVE LEAF TESTS" in tests:
        raise ValueError("DEVNIRA V2 native leaf already patched")
    if code.count(anchor) != 1 or "fn amount_leaf(amount: u128)" not in tests:
        raise ValueError("Unexpected ZK tree source revision; refusing unsafe leaf patch")
    code=code.replace(anchor,V2_HASH_FN+anchor,1)
    tests=tests+"\n"+V2_TESTS
    code_file.write_text(code)
    tests_file.write_text(tests)
    print("Added exact 8-decimal u64 ZK leaf hash and oversupply/one-base-unit FRAME tests.")
    print("V1 active leaf unchanged; cross-layer V2 migration still required.")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("upstream_root",type=Path)
    patch(parser.parse_args().upstream_root)
