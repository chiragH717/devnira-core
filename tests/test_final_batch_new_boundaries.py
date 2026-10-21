"""DEFERRED regression cases for one FINAL integration run; not proof of live funds/GPU."""
import unittest
from pathlib import Path
import tempfile
from spec.ss58_company_account import encode_ss58_account
from scripts.dvn_unsigned_dev_signing_intent import build_intent,SigningIntentRejected
from scripts.dvn_v2_consensus_root_probe import (
    xxh64,twox128,value_key,history_key,root_in_finalized_state,V2RootRejected)
from scripts.dvn_physical_gpu_probe import scan,require,GpuHardwareMissing

GEN="0x"+"1"*64
HEAD="0x"+"2"*64
OWNER=encode_ss58_account(bytes([7])*32)
TARGET=encode_ss58_account(bytes([8])*32)
def account(n,free):
    return "0x"+(n.to_bytes(4,"little")+
        (0).to_bytes(4,"little")+(1).to_bytes(4,"little")+
        (0).to_bytes(4,"little")+
        free.to_bytes(16,"little")+(0).to_bytes(16,"little")+
        (0).to_bytes(16,"little")+(1<<127).to_bytes(16,"little")).hex()

class RpcStub:
    def __init__(self):self.bad_peer=False;self.foreign=False;self.drift=False
    def __call__(self,url,name,params=None):
        if name=="chain_getFinalizedHead":return HEAD
        if name=="chain_getHeader":return {"number":"0x2"}
        if name=="chain_getBlockHash":return GEN if params==[0] else HEAD
        if name=="state_getRuntimeVersion":
            return {"specName":"devnira-8dec-native-dev-test-runtime",
                    "specVersion":1,"transactionVersion":1}
        if name=="system_properties":
            return {"tokenDecimals":12 if self.foreign else 8,
                    "tokenSymbol":"DVN","ss58Format":190}
        if name=="system_peers":return [] if self.bad_peer else [{"peerId":"DEV_ONLY"}]
        if name=="state_getMetadata":return "0x6d657461"
        if name=="state_getStorage":
            key,block=params
            if block!=HEAD:raise ValueError("bad state anchor")
            if key.startswith("0xc2261276"):return "0x"+(100000).to_bytes(16,"little").hex()
            from scripts.dvn_signed_transfer_acceptance import account_key
            if key==account_key(OWNER):
                return account(8 if self.drift and url.endswith("19542") else 7,10000000)
            return account(0,1000)
        raise ValueError("unexpected RPC "+name)

class DeferredFinalBatchTests(unittest.TestCase):
    def test_frame_twox_hash_known_vectors(self):
        self.assertEqual(xxh64(b""),0xef46db3751d8e999)
        self.assertEqual(xxh64(b"a"),0xd24ec4f1a98c6e5b)
        self.assertEqual(len(twox128(b"System")),16)
        self.assertEqual(len(bytes.fromhex(history_key(2)[2:])),32+8+4)
    def test_build_immutable_unsigned_intent_from_two_same_finalized_peers(self):
        s=RpcStub()
        r=build_intent(node_a="http://127.0.0.1:19541",
            node_b="http://127.0.0.1:19542",trusted_genesis=GEN,
            from_address=OWNER,to_address=TARGET,amount_units=100,
            fee_limit_units=20,transport=s)
        self.assertEqual(r["intent"]["nonce"],7)
        self.assertTrue(r["intent"]["contains_signed_payload"] is False)
        self.assertTrue(r["intent_sha256"])
        self.assertIsNone(r["signed_extrinsic"])
    def test_wrong_dev_network_peers_or_nonce_rejected(self):
        for prop in ("foreign","bad_peer","drift"):
            s=RpcStub();setattr(s,prop,True)
            with self.subTest(prop=prop),self.assertRaises((SigningIntentRejected,ValueError)):
                build_intent(node_a="http://127.0.0.1:19541",
                    node_b="http://127.0.0.1:19542",trusted_genesis=GEN,
                    from_address=OWNER,to_address=TARGET,amount_units=100,
                    fee_limit_units=20,transport=s)
    def test_default_disabled_v2_mode_must_block(self):
        def fake(url,name,params=None):
            if name=="state_getStorage":return "0x00"
            raise AssertionError("no V2 real state was checked")
        with self.assertRaisesRegex(V2RootRejected,"INACTIVE"):
            root_in_finalized_state("http://127.0.0.1:19541",HEAD,2,transport=fake)
    def test_actual_v2_root_and_history_field_contract(self):
        root=bytes([11])*32;count=(3).to_bytes(8,"little")
        storage={
            value_key("System","DvnV2HeaderMode"):"0x01",
            value_key("Wormhole","DvnV2TreeRoot"):"0x"+root.hex(),
            value_key("Wormhole","DvnV2TreeCount"):"0x"+count.hex(),
            history_key(2):"0x"+(root+count).hex()}
        def fake(url,name,params=None):
            if name=="state_getStorage":return storage[params[0]]
            if name=="chain_getHeader":return {"number":"0x2","zkTreeRoot":"0x"+root.hex()}
            raise AssertionError(name)
        got=root_in_finalized_state("http://127.0.0.1:19541",HEAD,2,transport=fake)
        self.assertEqual(got["leaf_count"],3)
        storage[history_key(2)]="0x"+(bytes([12])*32+count).hex()
        with self.assertRaisesRegex(V2RootRejected,"snapshot"):
            root_in_finalized_state("http://127.0.0.1:19541",HEAD,2,transport=fake)
    def test_physical_gpu_must_have_real_sysfs_driver_and_no_cpu_substitution(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/"drm";root.mkdir()
            with self.assertRaises(GpuHardwareMissing):
                require(scan(root),nvidia=True,amd=True)
            d=root/"card0"/"device";d.mkdir(parents=True)
            (d/"vendor").write_text("0x10de\n")
            driver=Path(t)/"nvidia";driver.mkdir()
            (d/"driver").symlink_to(driver,target_is_directory=True)
            out=scan(root)
            self.assertEqual(out["physical_vendor_count"]["NVIDIA"],1)
            self.assertFalse(out["actual_qpow_nonce_verified"])
            with self.assertRaisesRegex(GpuHardwareMissing,"AMD"):
                require(out,nvidia=True,amd=True)
if __name__=="__main__":unittest.main()
