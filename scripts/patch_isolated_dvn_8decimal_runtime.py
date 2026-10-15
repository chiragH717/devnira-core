#!/usr/bin/env python3
"""Build an isolated DVN 8-decimal native/WASM FRAME *research* runtime.

The locked upstream ZK verifier is still 4.3.0 / V1 12 decimals. To avoid
enabling unspendable coins, all dispatchable user calls are DISABLED with an
allowlist restricted to System / Timestamp; this makes the dev runtime
INTENTIONALLY NON-TRANSACTING. It cannot be mainnet or a working wallet.
An independent V2 native+WASM runtime must replace this research build.
"""
import argparse
from pathlib import Path

RUNTIME_MARKER="DEVNIRA ISOLATED EIGHT DECIMAL RUNTIME - NO USER TRANSFERS"
FILTER_MARKER="DEVNIRA INERT 8-DECIMAL RESEARCH: ALL USER PAYMENTS DISABLED"

def change_once(s: str, old: str, new: str, reason: str) -> str:
    if s.count(old)!=1:
        raise ValueError(f"STOP: exact upstream source changed ({reason}): {s.count(old)} occurrences")
    return s.replace(old,new,1)

def patch(root:Path)->None:
    rt=root/"runtime/src/lib.rs"
    cfg=root/"runtime/src/configs/mod.rs"
    spec=root/"node/src/chain_spec.rs"
    cmd=root/"node/src/command.rs"
    manifest=root/"Cargo.toml"
    legacy_preset=root/"runtime/src/genesis_config_presets/mainnet_vesting.rs"
    texts={p:p.read_text(encoding="utf-8") for p in (rt,cfg,spec,cmd,manifest,legacy_preset)}
    if RUNTIME_MARKER in texts[rt] or FILTER_MARKER in texts[cfg]:
        raise ValueError("STOP: research-only 8-decimal runtime already applied")
    if "DEVNIRA PRE-RELEASE: only --chain dev or --chain devnira-local" not in texts[cmd]:
        raise ValueError("STOP: first disable all Quantus public network selectors")
    if '"=4.3.0"' not in texts[manifest]:
        raise ValueError("STOP: upstream proof crates changed; re-audit isolation assumptions")
    if "pub const AMOUNT_SCALE_DOWN_FACTOR: u128 = 10_000_000_000;" not in (
            root/"pallets/zk-tree/src/tree.rs").read_text():
        raise ValueError("STOP: V1 leaf amount scale changed; re-audit entire proof path")
    if "pub const SCALE_DOWN_FACTOR: u128 = 10_000_000_000;" not in (
            root/"pallets/wormhole/src/lib.rs").read_text():
        raise ValueError("STOP: V1 withdrawal amount scale changed; re-audit")
    s=texts[rt]
    s=change_once(s,'spec_name: alloc::borrow::Cow::Borrowed("quantus-runtime"),',
                    'spec_name: alloc::borrow::Cow::Borrowed("devnira-8dec-inert-dev-runtime"),',
                    "spec name")
    s=change_once(s,'impl_name: alloc::borrow::Cow::Borrowed("quantus-runtime"),',
                    'impl_name: alloc::borrow::Cow::Borrowed("devnira-8dec-inert-dev-runtime"),',
                    "impl name")
    for old,new in (
        ("pub const UNIT: Balance = 1_000_000_000_000;",
         "pub const UNIT: Balance = 100_000_000;"),
        ("pub const MILLI_UNIT: Balance = 1_000_000_000;",
         "pub const MILLI_UNIT: Balance = 100_000;"),
        ("pub const MICRO_UNIT: Balance = 1_000_000;",
         "pub const MICRO_UNIT: Balance = 100;"),
        ("pub const MAX_SUPPLY: Balance = 21_000_000 * UNIT;",
         "pub const MAX_SUPPLY: Balance = 100_000_000 * UNIT;"),
    ):
        s=change_once(s,old,new,old)
    s=s.replace("/// Hard cap on total issuance; mining emissions stop here.",
        "// "+RUNTIME_MARKER+"\n/// Hard cap on total issuance; mining emissions stop here.",1)

    conf=texts[cfg]
    conf=change_once(conf,"pub const SS58Prefix: u8 = 189;",
                          "pub const SS58Prefix: u8 = 190;","network address prefix")
    # Explicit allowlist is stronger than trying to blacklist one V1 exit:
    # until V2 native proof/authenticator is active NO USER TRANSACTIONS may
    # be submitted. Even balances transfer / vesting/governance is forbidden
    # in this non-economic dev fixture. This does not block inherent hooks,
    # so do NOT run a public rewards network with this node.
    filter_source=(
        "// "+FILTER_MARKER+"\n"
        "pub struct DvnResearchOnlyCallFilter;\n"
        "impl frame_support::traits::Contains<RuntimeCall> for DvnResearchOnlyCallFilter {\n"
        "\tfn contains(call: &RuntimeCall) -> bool {\n"
        "\t\tmatches!(call, RuntimeCall::Timestamp(_) | RuntimeCall::System(_))\n"
        "\t}\n"
        "}\n\n"
    )
    anchor="#[derive_impl(frame_system::config_preludes::SolochainDefaultConfig)]"
    conf=change_once(conf,anchor,filter_source+anchor,"FRAME base-call filter insertion")
    conf=change_once(conf,"\ttype Block = Block;", "\ttype Block = Block;\n"
             "\t// No balances/wormhole/vesting/user extrinsics while V1 proofs remain.\n"
             "\ttype BaseCallFilter = DvnResearchOnlyCallFilter;",
             "FRAME system call restriction")

    chain=texts[spec]
    # The dev spec stays DEVELOPMENT ONLY, with demo genesis accounts.
    prefix="pub fn development_chain_spec() -> Result<ChainSpec, String> {"
    idx=chain.index(prefix)
    end=chain.index("\n}\n",idx)+2
    dev=chain[idx:end]
    for old,new in (
        ('json!(12)','json!(8)'),
        ('json!("DEV")','json!("DVN")'),
        ('json!(189)','json!(190)'),
        ('"Quantus DevNet wasm not available"','"DEVNIRA isolated research WASM unavailable"'),
        ('"Quantus DevNet"','"DEVNIRA isolated 8-decimal research / NO SEND"'),
        ('"dev"','"devnira-8dec-inert-dev"'),
        ('"quantus-devnet"','"devnira-8dec-inert-dev"'),
    ):
        dev=change_once(dev,old,new,"DEVNIRA development chain spec "+old)
    chain=chain[:idx]+dev+chain[end:]

    # Rust E0080 regression: the inherited Quantus mainnet spreadsheet has
    # compile-time checks against 21M QTC at 12 decimals. Changing Runtime
    # UNIT/MAX_SUPPLY to DVN must NOT reinterpret that old allocation as DVN,
    # remove any of the checks, or mint its funds in the development chain.
    # Isolate the old, UNREACHABLE preset's own original economics, while the
    # CLI strictly rejects the 'mainnet' selector. This is NOT DVN genesis.
    legacy=texts[legacy_preset]
    legacy=change_once(legacy,
        "use crate::{AccountId, MAX_SUPPLY, UNIT};",
        "use crate::AccountId;",
        "upstream Quantus mainnet allocation import")
    import re
    if legacy.count("pub const GENESIS_ALLOCATION: u128 = 27 * MAX_SUPPLY / 100;")!=1:
        raise ValueError("STOP: legacy Quantus 21M genesis economics changed")
    if legacy.count("const _: () = assert!(GENESIS_ALLOCATION == 5_670_000 * UNIT);")!=1:
        raise ValueError("STOP: old Quantus allocation assertions changed")
    legacy=re.sub(r"\bMAX_SUPPLY\b","LEGACY_QTC_MAX_SUPPLY",legacy)
    legacy=re.sub(r"\bUNIT\b","LEGACY_QTC_UNIT",legacy)
    legacy=legacy.replace("use crate::AccountId;",
        "use crate::AccountId;\n"
        "// INERT RESEARCH ONLY: isolated unreachable Quantus 12-decimal mainnet\n"
        "// allocation. Preserve ALL original compile-time accounting checks.\n"
        "// Never reuse these balances or beneficiaries in DVN genesis.\n"
        "const LEGACY_QTC_UNIT: u128 = 1_000_000_000_000;\n"
        "const LEGACY_QTC_MAX_SUPPLY: u128 = 21_000_000 * LEGACY_QTC_UNIT;",
        1)
    if "pub const GENESIS_ALLOCATION: u128 = 27 * LEGACY_QTC_MAX_SUPPLY / 100;" not in legacy:
        raise ValueError("STOP: failed to isolate old mainnet supply from DVN runtime")
    if "const _: () = assert!(GENESIS_ALLOCATION == 5_670_000 * LEGACY_QTC_UNIT);" not in legacy:
        raise ValueError("STOP: no preserved original Quantus genesis invariant")
    if "const _: () = assert!(vesting_total() + SEEDED_ACCOUNTS * SEED == GENESIS_ALLOCATION);" not in legacy:
        raise ValueError("STOP: inherited allocation-sum assertion changed")
    # Recheck the pre-commit invariants before modifying any actual source.
    assert "RuntimeCall::Wormhole" not in filter_source
    assert 'matches!(call, RuntimeCall::Timestamp(_) | RuntimeCall::System(_))' in conf
    for p,body in ((rt,s),(cfg,conf),(spec,chain),(legacy_preset,legacy)):
        p.write_text(body,encoding="utf-8")
    print("Built isolated 8-decimal runtime source (DVN / SS58-190 / 100M metadata).")
    print("ALL USER FINANCIAL TRANSACTIONS DISABLED; V1 4.3 proofs still present.")
    print("FOR RESEARCH BUILDS ONLY. Cannot distribute as live chain, miner or wallet.")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("exact_pinned_chain_source",type=Path)
    patch(parser.parse_args().exact_pinned_chain_source)
