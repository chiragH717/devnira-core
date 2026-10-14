#!/usr/bin/env python3
"""Stage real upstream wormhole-inputs V2 leaf/private/public batch parsers.

Opt-in standalone, no V1 mutation, no false V2 activation. The attached
test workflow compiles and runs these parsers in the exact pinned Rust crate.
"""
from pathlib import Path
import argparse

MARKER = "pub mod devnira_v2_public_inputs;"
V2_RUST = r'''//! DEVNIRA V2 exact native eight-decimal amount public-input decoder.
//!
//! This is an INACTIVE, side-by-side source candidate. Do not treat a parsed
//! proof as verified: matching V2 circuit hashes, verifier keys, recursive
//! verifier constraints, block binding and on-chain nullifier rules are mandatory.
//!
//! V1 uses u32 quantized amounts. V2 uses a single canonical Goldilocks felt
//! carrying exact native u64 base units, with a per-leaf 100M DVN hard cap.
//! No amount is rounded, saturated, or silently converted back to u32.
use alloc::vec::Vec;
use anyhow::{bail, ensure, Context, Result};
use super::{
    hash_u64s_to_bytes_digest, public_batch_pi, validate_proof_count,
    BytesDigest, ASSET_ID_INDEX, OUTPUT_AMOUNT_1_INDEX, OUTPUT_AMOUNT_2_INDEX,
    VOLUME_FEE_BPS_INDEX, NULLIFIER_START_INDEX, NULLIFIER_END_INDEX,
    EXIT_ACCOUNT_1_START_INDEX, EXIT_ACCOUNT_1_END_INDEX,
    EXIT_ACCOUNT_2_START_INDEX, EXIT_ACCOUNT_2_END_INDEX,
    BLOCK_HASH_START_INDEX, BLOCK_HASH_END_INDEX, BLOCK_NUMBER_INDEX,
    INPUT_AMOUNT_INDEX, PUBLIC_INPUTS_FELTS_LEN,
};

pub const DVN_MAX_BASE_UNITS: u64 = 10_000_000_000_000_000;
pub const DVN_GOLDILOCKS_PRIME: u64 = 0xFFFF_FFFF_0000_0001;
pub const DVN_V2_AMOUNT_DECIMALS: u32 = 8;

/// A parser does NOT authenticate that proof carries a V2 verifier artifact.
/// No V1->V2 reinterpretation is permitted for production verification.
fn check_felts(pis: &[u64]) -> Result<()> {
    ensure!(pis.iter().all(|v| *v < DVN_GOLDILOCKS_PRIME),
        "DVN V2 noncanonical Goldilocks public input");
    Ok(())
}
fn read_u32(raw: u64, label: &str) -> Result<u32> {
    u32::try_from(raw).with_context(|| alloc::format!("DVN V2 {label} exceeds u32"))
}
fn read_amount(raw: u64, label: &str) -> Result<u64> {
    ensure!(raw < DVN_GOLDILOCKS_PRIME, "DVN V2 {label} noncanonical");
    ensure!(raw <= DVN_MAX_BASE_UNITS, "DVN V2 {label} above 100M cap");
    Ok(raw)
}
fn read_bps(raw: u64) -> Result<u32> {
    let value=read_u32(raw,"volume_fee_bps")?;
    ensure!(value <= 10_000, "DVN V2 basis-point rate above 100%");
    Ok(value)
}
fn digest(pis: &[u64]) -> Result<BytesDigest> {
    hash_u64s_to_bytes_digest(pis)
}
fn bound_aggregate_total(values: impl Iterator<Item=u64>) -> Result<()> {
    let mut sum: u128=0;
    for amount in values {
        sum=sum.checked_add(amount as u128)
            .ok_or_else(|| anyhow::anyhow!("DVN V2 aggregate u128 overflow"))?;
        ensure!(sum <= DVN_MAX_BASE_UNITS as u128,
            "DVN V2 aggregate exits above 100M minted supply");
    }
    Ok(())
}

#[derive(Clone, PartialEq, Eq)]
pub struct DvnV2LeafPublicInputs {
    pub asset_id: u32,
    pub output_amount_1: u64,
    pub output_amount_2: u64,
    pub volume_fee_bps: u32,
    pub nullifier: BytesDigest,
    pub exit_account_1: BytesDigest,
    pub exit_account_2: BytesDigest,
    pub block_hash: BytesDigest,
    pub block_number: u32,
    pub input_amount: u64,
}
impl core::fmt::Debug for DvnV2LeafPublicInputs {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        f.debug_struct("DvnV2LeafPublicInputs")
            .field("asset_id",&self.asset_id)
            .field("output_amount_1",&self.output_amount_1)
            .field("output_amount_2",&self.output_amount_2)
            .field("volume_fee_bps",&self.volume_fee_bps)
            .field("block_hash",&self.block_hash)
            .field("block_number",&self.block_number)
            .field("input_amount",&"[REDACTED]")
            .finish()
    }
}
impl DvnV2LeafPublicInputs {
    pub fn try_from_u64_slice(pis: &[u64]) -> Result<Self> {
        ensure!(pis.len()==PUBLIC_INPUTS_FELTS_LEN,
            "DVN V2 leaf requires exactly 22 public felts");
        check_felts(pis)?;
        let asset_id=read_u32(pis[ASSET_ID_INDEX],"asset_id")?;
        let output_amount_1=read_amount(pis[OUTPUT_AMOUNT_1_INDEX],"output_amount_1")?;
        let output_amount_2=read_amount(pis[OUTPUT_AMOUNT_2_INDEX],"output_amount_2")?;
        let input_amount=read_amount(pis[INPUT_AMOUNT_INDEX],"input_amount")?;
        let output_total=output_amount_1.checked_add(output_amount_2)
            .ok_or_else(|| anyhow::anyhow!("DVN V2 sum overflow"))?;
        ensure!(output_total <= input_amount,
            "DVN V2 outputs exceed authenticated input");
        Ok(Self {
            asset_id, output_amount_1, output_amount_2,
            volume_fee_bps:read_bps(pis[VOLUME_FEE_BPS_INDEX])?,
            nullifier:digest(&pis[NULLIFIER_START_INDEX..NULLIFIER_END_INDEX])?,
            exit_account_1:digest(&pis[EXIT_ACCOUNT_1_START_INDEX..EXIT_ACCOUNT_1_END_INDEX])?,
            exit_account_2:digest(&pis[EXIT_ACCOUNT_2_START_INDEX..EXIT_ACCOUNT_2_END_INDEX])?,
            block_hash:digest(&pis[BLOCK_HASH_START_INDEX..BLOCK_HASH_END_INDEX])?,
            block_number:read_u32(pis[BLOCK_NUMBER_INDEX],"block_number")?,
            input_amount,
        })
    }
    pub fn unallocated_fee_units(&self) -> u64 {
        self.input_amount - self.output_amount_1 - self.output_amount_2
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DvnV2Exit {
    pub amount: u64,
    pub account: BytesDigest,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DvnV2PrivateBatchPublicInputs {
    pub num_exit_slots: u32,
    pub asset_id: u32,
    pub volume_fee_bps: u32,
    pub block_hash: BytesDigest,
    pub block_number: u32,
    pub exits: Vec<DvnV2Exit>,
    pub nullifiers: Vec<BytesDigest>,
}
impl DvnV2PrivateBatchPublicInputs {
    pub fn try_from_u64_slice(pis: &[u64]) -> Result<Self> {
        check_felts(pis)?;
        let payload=pis.len().checked_sub(8)
            .filter(|len| *len % PUBLIC_INPUTS_FELTS_LEN == 0)
            .ok_or_else(|| anyhow::anyhow!("DVN V2 private-batch malformed length"))?;
        let n_leaf=payload/PUBLIC_INPUTS_FELTS_LEN;
        validate_proof_count(n_leaf,"DVN V2 private-batch leaf count")?;
        let num_exit_slots=read_u32(pis[0],"private-batch num_exit_slots")?;
        ensure!(num_exit_slots as usize == n_leaf*2,
            "DVN V2 private-batch structural exit count mismatch");
        let asset_id=read_u32(pis[1],"private-batch asset_id")?;
        let volume_fee_bps=read_bps(pis[2])?;
        let block_hash=digest(&pis[3..7])?;
        let block_number=read_u32(pis[7],"private-batch block_number")?;
        let mut cursor=8;
        let mut exits=Vec::with_capacity(n_leaf*2);
        for _ in 0..n_leaf*2 {
            let amount=read_amount(pis[cursor],"private-batch output sum")?;
            cursor+=1;
            let account=digest(&pis[cursor..cursor+4])?;
            cursor+=4;
            exits.push(DvnV2Exit{amount,account});
        }
        let mut nullifiers=Vec::with_capacity(n_leaf);
        for _ in 0..n_leaf {
            nullifiers.push(digest(&pis[cursor..cursor+4])?);
            cursor+=4;
        }
        ensure!(cursor==pis.len(),"DVN V2 private-batch trailing public inputs");
        bound_aggregate_total(exits.iter().map(|x|x.amount))?;
        Ok(Self{num_exit_slots,asset_id,volume_fee_bps,block_hash,block_number,exits,nullifiers})
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DvnV2PublicBatchPublicInputs {
    pub aggregator_address: BytesDigest,
    pub asset_id: u32,
    pub volume_fee_bps: u32,
    pub block_hash: BytesDigest,
    pub block_number: u32,
    pub total_exit_slots: u32,
    pub exits: Vec<DvnV2Exit>,
    pub nullifiers: Vec<BytesDigest>,
}
impl DvnV2PublicBatchPublicInputs {
    pub fn try_from_u64_slice(pis: &[u64], n_private: usize, n_leaf: usize) -> Result<Self> {
        validate_proof_count(n_private,"DVN V2 public-batch private count")?;
        validate_proof_count(n_leaf,"DVN V2 public-batch leaf count")?;
        let expected=public_batch_pi::try_pi_len(n_private,n_leaf)
            .ok_or_else(|| anyhow::anyhow!("DVN V2 public-batch layout overflow"))?;
        ensure!(pis.len()==expected,"DVN V2 public-batch malformed length");
        check_felts(pis)?;
        let slots=n_private.checked_mul(n_leaf).and_then(|x|x.checked_mul(2))
            .ok_or_else(|| anyhow::anyhow!("DVN V2 public-batch slots overflow"))?;
        let actual_slots=read_u32(pis[11],"public-batch total_exit_slots")?;
        ensure!(actual_slots as usize==slots,
            "DVN V2 public-batch structural exit slot mismatch");
        let aggregator_address=digest(&pis[0..4])?;
        let asset_id=read_u32(pis[4],"public-batch asset_id")?;
        let volume_fee_bps=read_bps(pis[5])?;
        let block_hash=digest(&pis[6..10])?;
        let block_number=read_u32(pis[10],"public-batch block_number")?;
        let mut cursor=12;
        let mut exits=Vec::with_capacity(slots);
        for _ in 0..slots {
            let amount=read_amount(pis[cursor],"public-batch output sum")?;
            cursor+=1;
            let account=digest(&pis[cursor..cursor+4])?;
            cursor+=4;
            exits.push(DvnV2Exit{amount,account});
        }
        let mut nullifiers=Vec::with_capacity(n_private*n_leaf);
        for _ in 0..n_private*n_leaf {
            nullifiers.push(digest(&pis[cursor..cursor+4])?);
            cursor+=4;
        }
        ensure!(cursor==pis.len(),"DVN V2 public-batch trailing public inputs");
        bound_aggregate_total(exits.iter().map(|x|x.amount))?;
        Ok(Self{
            aggregator_address,asset_id,volume_fee_bps,block_hash,block_number,
            total_exit_slots:actual_slots,exits,nullifiers,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn leaf(input:u64,out1:u64,out2:u64) -> Vec<u64> {
        let mut pi=alloc::vec![0u64;PUBLIC_INPUTS_FELTS_LEN];
        pi[INPUT_AMOUNT_INDEX]=input;
        pi[OUTPUT_AMOUNT_1_INDEX]=out1;
        pi[OUTPUT_AMOUNT_2_INDEX]=out2;
        pi
    }
    #[test]
    fn dvn_v2_leaf_preserves_full_precision_above_u32() {
        for amount in [0,1,5_000_000_000,58_333_333_333_333,DVN_MAX_BASE_UNITS] {
            let pi=leaf(amount,amount,0);
            let v=DvnV2LeafPublicInputs::try_from_u64_slice(&pi).unwrap();
            assert_eq!(v.input_amount,amount);
            assert_eq!(v.output_amount_1,amount);
            assert_eq!(v.unallocated_fee_units(),0);
            if amount > u32::MAX as u64 {
                assert!(crate::PublicCircuitInputs::try_from_u64_slice(&pi).is_err(),
                    "quantized V1 parser must not recognize V2 large native amount");
            }
        }
    }
    #[test]
    fn dvn_v2_leaf_rejects_inflation_bps_and_noncanonical() {
        for pi in [
            leaf(1,2,0),
            leaf(DVN_MAX_BASE_UNITS + 1,0,0),
            leaf(1,DVN_MAX_BASE_UNITS+1,0),
        ] {
            assert!(DvnV2LeafPublicInputs::try_from_u64_slice(&pi).is_err());
        }
        let mut bad=leaf(1,1,0);
        bad[VOLUME_FEE_BPS_INDEX]=10_001;
        assert!(DvnV2LeafPublicInputs::try_from_u64_slice(&bad).is_err());
        bad[VOLUME_FEE_BPS_INDEX]=0;
        bad[ASSET_ID_INDEX]=DVN_GOLDILOCKS_PRIME;
        assert!(DvnV2LeafPublicInputs::try_from_u64_slice(&bad).is_err());
        assert!(DvnV2LeafPublicInputs::try_from_u64_slice(&[0u64;21]).is_err());
    }
    #[test]
    fn dvn_v2_private_batch_decodes_u64_exits_and_rejects_overcap() {
        // 8 header + 2 exits*5 + 1 nullifier*4 = 22+8 felts.
        let mut pis=alloc::vec![0u64;30];
        pis[0]=2;pis[8]=5_000_000_000;pis[13]=1;
        let v=DvnV2PrivateBatchPublicInputs::try_from_u64_slice(&pis).unwrap();
        assert_eq!(v.exits[0].amount,5_000_000_000);
        assert_eq!(v.exits[1].amount,1);
        pis[0]=1;
        assert!(DvnV2PrivateBatchPublicInputs::try_from_u64_slice(&pis).is_err());
        pis[0]=2;pis[13]=DVN_MAX_BASE_UNITS;
        assert!(DvnV2PrivateBatchPublicInputs::try_from_u64_slice(&pis).is_err());
        pis[13]=1;pis[8]=DVN_MAX_BASE_UNITS + 1;
        assert!(DvnV2PrivateBatchPublicInputs::try_from_u64_slice(&pis).is_err());
    }
    #[test]
    fn dvn_v2_public_batch_u64_exits_are_not_u32() {
        // 12 header + 2 exits*5 + 1 nullifier*4 = 26 felts.
        let mut pis=alloc::vec![0u64;26];
        pis[11]=2;pis[12]=5_000_000_000;pis[17]=1;
        let v=DvnV2PublicBatchPublicInputs::try_from_u64_slice(&pis,1,1).unwrap();
        assert_eq!(v.total_exit_slots,2);
        assert_eq!(v.exits[0].amount,5_000_000_000);
        pis[11]=3;
        assert!(DvnV2PublicBatchPublicInputs::try_from_u64_slice(&pis,1,1).is_err());
        pis[11]=2;pis[12]=DVN_MAX_BASE_UNITS;pis[17]=1;
        assert!(DvnV2PublicBatchPublicInputs::try_from_u64_slice(&pis,1,1).is_err());
        assert!(DvnV2PublicBatchPublicInputs::try_from_u64_slice(&pis,0,1).is_err());
        assert!(DvnV2PublicBatchPublicInputs::try_from_u64_slice(&pis,1,0).is_err());
    }
}
'''

def patch(root: Path) -> None:
    base=root/"wormhole/inputs/src"
    lib=base/"lib.rs"
    module=base/"devnira_v2_public_inputs.rs"
    code=lib.read_text(encoding="utf-8")
    if module.exists() or MARKER in code:
        raise ValueError("STOP: native V2 public-input decoder already installed")
    for expected in (
        "pub struct PublicCircuitInputs",
        "pub output_amount_1: u32",
        "pub input_amount: u32",
        "pub struct PublicBatchPublicInputs",
        "pub const PUBLIC_INPUTS_FELTS_LEN: usize = 22;",
        "pub mod public_batch_pi",
        "fn hash_u64s_to_bytes_digest",
    ):
        if expected not in code:
            raise ValueError(f"STOP: upstream V1 codec drift at {expected}")
    module.write_text(V2_RUST,encoding="utf-8")
    lib.write_text(code+"\n// V2 opt-in parser only: V1 circuit and verifier are UNCHANGED.\n"+MARKER+"\n",encoding="utf-8")
    print("Staged typed native u64 V2 leaf, private-batch and public-batch parsers.")
    print("STOP: this does not change active V1 circuit, recursive proofs, verifier or runtime.")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("upstream_zk_source",type=Path)
    patch(ap.parse_args().upstream_zk_source)
