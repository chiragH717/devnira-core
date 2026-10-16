import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from scripts.verify_v2_dev_vk_artifacts import KEY_FILES,V2FingerprintRejected,verify_development_vk,PINS

class V2DeveloperKeyPinTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.artifacts=self.root/"artifacts"
        self.artifacts.mkdir()
        base=Path(__file__).resolve().parents[1]/"config/dvn-v2-dev-vk-fingerprints.json"
        self.policy=json.loads(base.read_text(encoding="utf-8"))
        self.config=self.root/"pins.json"
        self.data={}
        for i,name in enumerate(KEY_FILES):
            payload=("DEVELOPMENT-FIXTURE-"+str(i)).encode()
            self.data[name]=payload
            (self.artifacts/name).write_bytes(payload)
            self.policy["sha256"][name]=hashlib.sha256(payload).hexdigest()
        self.save()
    def save(self):
        self.config.write_text(json.dumps(self.policy),encoding="utf-8")
    def check(self):
        return verify_development_vk(self.artifacts,config=self.config,pins=PINS)
    def test_both_key_and_common_bytes_checked(self):
        report=self.check()
        self.assertEqual(report["keys_and_common_data_verified"],4)
        self.assertFalse(report["production_vk_approved"])
        self.assertFalse(report["release_allowed"])
    def test_every_artifact_tamper_fails(self):
        for name in KEY_FILES:
            path=self.artifacts/name
            original=path.read_bytes()
            path.write_bytes(original+b"X")
            with self.subTest(name=name),self.assertRaisesRegex(V2FingerprintRejected,"VERIFIER DRIFT"):
                self.check()
            path.write_bytes(original)
    def test_missing_empty_symlink_extra_key_fail(self):
        p=self.artifacts/KEY_FILES[0]
        p.unlink()
        with self.assertRaises(V2FingerprintRejected):self.check()
        p.write_bytes(b"")
        with self.assertRaises(V2FingerprintRejected):self.check()
        p.unlink()
        p.symlink_to(self.artifacts/KEY_FILES[1])
        with self.assertRaises(V2FingerprintRejected):self.check()
        p.unlink()
        p.write_bytes(self.data[KEY_FILES[0]])
        self.policy["sha256"]["foreign.bin"]="0"*64
        self.save()
        with self.assertRaises(V2FingerprintRejected):self.check()
    def test_chain_circuit_abi_and_release_flags_fail(self):
        for key,value in [
            ("circuit_pin","f"*40),("chain_pin","f"*40),
            ("public_inputs",{"private":24,"public":46}),
            ("production_vk_approved",True),("runtime_vk_embedded",True),
            ("deposit_backing_verified",True),("release_allowed",True),
            ("classification","PRODUCTION")
        ]:
            old=self.policy[key]
            self.policy[key]=value
            self.save()
            with self.subTest(key=key),self.assertRaises(V2FingerprintRejected):self.check()
            self.policy[key]=old
            self.save()
    def test_noncanonical_digest_rejected(self):
        self.policy["sha256"][KEY_FILES[1]]="A"*64
        self.save()
        with self.assertRaises(V2FingerprintRejected):self.check()

if __name__=="__main__":
    unittest.main()
