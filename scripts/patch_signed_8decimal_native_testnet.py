#!/usr/bin/env python3
"""Strictly isolated 8-decimal native BALANCES-only signed transaction testnet.

Run after guard_dvn_network_identity and inert 8decimal source patch. No
Wormhole/old-ZK proof calls; no mainnet or independent company genesis.
SECURITY: DOES NOT activate V2 and does NOT prove signed transfer success.
"""
import argparse
from pathlib import Path
MARKER="DEVNIRA_DEV_ONLY_SIGNED_NATIVE_BALANCES_WITHOUT_V1_WORMHOLE"
FILTER_BEFORE="matches!(call, RuntimeCall::Timestamp(_) | RuntimeCall::System(_))"
FILTER_AFTER="""matches!(call,
                RuntimeCall::Timestamp(_) | RuntimeCall::System(_)
                | RuntimeCall::Balances(pallet_balances::Call::transfer_keep_alive { .. })
            )"""
RECORDER="\ttransaction_extensions::WormholeProofRecorderExtension<Runtime>,\n"

def single(src,old,new,reason):
    count=src.count(old)
    if count!=1:
        raise ValueError("STOP: pinned upstream source drift at "+reason+" count="+str(count))
    return src.replace(old,new,1)

def patch(root:Path):
    runtime=root/"runtime/src/lib.rs"
    cfg=root/"runtime/src/configs/mod.rs"
    chains=root/"node/src/chain_spec.rs"
    code=runtime.read_text(encoding="utf-8")
    config=cfg.read_text(encoding="utf-8")
    spec=chains.read_text(encoding="utf-8")
    if MARKER in code:
        raise ValueError("STOP: native-only signed testnet already installed")
    for item in (
        "DEVNIRA ISOLATED EIGHT DECIMAL RUNTIME - NO USER TRANSFERS",
        "pub const UNIT: Balance = 100_000_000;",
        'spec_name: alloc::borrow::Cow::Borrowed("devnira-8dec-inert-dev-runtime"),'
    ):
        if item not in code: raise ValueError("STOP: pre-existing 8-decimal inert fork missing: "+item)
    if ("DEVNIRA INERT 8-DECIMAL RESEARCH: ALL USER PAYMENTS DISABLED" not in config
        or 'type BaseCallFilter = DvnResearchOnlyCallFilter;' not in config):
        raise ValueError("STOP: legacy restricted dispatch filter missing")
    if RECORDER not in code:
        raise ValueError("STOP: old V1 transaction proof recorder missing")
    if spec.count('devnira-8dec-inert-dev')!=2:
        raise ValueError("STOP: isolated 8-decimal chain identity changed")
    # Preserve signed nonce, fees, CheckGenesis, Spec/TxVersion and
    # CheckMetadataHash. Disable the legacy V1 event -> 12decimal leaf hook.
    code=single(code,RECORDER,"", "remove 12-decimal V1 proof recorder")
    code=single(code,
      'spec_name: alloc::borrow::Cow::Borrowed("devnira-8dec-inert-dev-runtime"),',
      'spec_name: alloc::borrow::Cow::Borrowed("devnira-8dec-native-dev-test-runtime"),',
      "separate signed native testnet runtime identity")
    code=single(code,
      'impl_name: alloc::borrow::Cow::Borrowed("devnira-8dec-inert-dev-runtime"),',
      'impl_name: alloc::borrow::Cow::Borrowed("devnira-8dec-native-dev-test-runtime"),',
      "separate signed native testnet implementation identity")
    code=code.replace(
      "// DEVNIRA ISOLATED EIGHT DECIMAL RUNTIME - NO USER TRANSFERS",
      "// DEVNIRA ISOLATED EIGHT DECIMAL RUNTIME - NO USER TRANSFERS\n"
      "// "+MARKER+"\n"
      "// Native signed Balances::transfer_keep_alive only, NO V1 proof recording.\n"
      "// Insecure development genesis keys ONLY. Never accept real DVN funds.",1)
    config=single(config,FILTER_BEFORE,FILTER_AFTER,"native signed keep-alive only")
    config=single(config,
       "// DEVNIRA INERT 8-DECIMAL RESEARCH: ALL USER PAYMENTS DISABLED",
       "// DEVNIRA INERT 8-DECIMAL RESEARCH: ALL USER PAYMENTS DISABLED\n"
       "// NATIVE DEV MODE ONLY: allow Balances keep_alive; no V1 proof recorder.",
       "retain legacy NO SEND warning")
    spec=spec.replace("devnira-8dec-inert-dev","devnira-8dec-native-dev-test")
    spec=single(spec,
        '"DEVNIRA isolated 8-decimal research / NO SEND"',
        '"DEVNIRA isolated 8-decimal NATIVE signed-transfer DEV TEST ONLY"',
        "explicit nonproduction dev identity")
    # Verify narrow and non-shielded callset before writing any files.
    assert "RuntimeCall::Wormhole" not in FILTER_AFTER
    assert "RuntimeCall::Utility" not in FILTER_AFTER
    assert "CheckGenesis<Runtime>" in code and "CheckNonce<Runtime>" in code
    assert "ChargeTransactionPayment<Runtime>" in code
    assert "WormholeProofRecorderExtension<Runtime>" not in code
    runtime.write_text(code,encoding="utf-8")
    cfg.write_text(config,encoding="utf-8")
    chains.write_text(spec,encoding="utf-8")
    print("STAGED: native-only signed balances development testnet source.")
    print("NOT V2 ACTIVE, NOT verified signed transactions, NOT independent company Genesis or mainnet.")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("pinned_frame_root",type=Path)
    patch(p.parse_args().pinned_frame_root)
