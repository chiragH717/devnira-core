import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from scripts.package_windows_company_bundle import (
    BundleRejected, NATIVE_EXE, GUI_EXE, NATIVE_HASH, GUI_HASH, package
)

class CompanyWalletPackaging(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name)
        self.native=root/"native"
        self.gui=root/"gui"
        self.native.mkdir()
        (self.gui/"dist").mkdir(parents=True)
        self.native_data=b"PRE-RELEASE TEST NATIVE BINARY; NOT FOR WALLET USE"
        self.gui_data=b"PRE-RELEASE TEST GUI BINARY; NOT FOR WALLET USE"
        self.native_exe=self.native/NATIVE_EXE
        self.gui_exe=self.gui/"dist"/GUI_EXE
        self.native_exe.write_bytes(self.native_data)
        self.gui_exe.write_bytes(self.gui_data)
        self.native_sha=hashlib.sha256(self.native_data).hexdigest()
        self.gui_sha=hashlib.sha256(self.gui_data).hexdigest()
        (self.native/NATIVE_HASH).write_text(self.native_sha+"  "+NATIVE_EXE+"\n")
        (self.gui/GUI_HASH).write_text(
            "Algorithm : SHA256\nHash : "+self.gui_sha.upper()+"\nPath : D:\\build\\dist\\"+GUI_EXE+"\n")
        self.out=root/"bundle.zip"

    def test_both_immutable_source_builds_verified_and_labeled_not_mainnet(self):
        result=package(self.native,self.gui,self.out)
        self.assertFalse(result["wallet_send_enabled"])
        self.assertFalse(result["independent_mainnet_active"])
        self.assertFalse(result["treasury_10m_minted"])
        self.assertEqual(result["native_cli"]["sha256"],self.native_sha)
        self.assertEqual(result["company_setup_gui"]["sha256"],self.gui_sha)
        with ZipFile(self.out) as archive:
            self.assertEqual(archive.namelist(),[
                NATIVE_EXE, GUI_EXE, "manifest.json", "READ-ME-FIRST.txt"])
            self.assertEqual(archive.read(NATIVE_EXE),self.native_data)
            self.assertEqual(archive.read(GUI_EXE),self.gui_data)
            self.assertIn("NOT a working worldwide DVN transaction wallet",
                          archive.read("READ-ME-FIRST.txt").decode())
            manifest=json.loads(archive.read("manifest.json"))
            self.assertFalse(manifest["wallet_send_enabled"])
        self.assertTrue(self.out.with_name(self.out.name+".sha256").is_file())

    def test_mismatched_native_or_gui_binary_refused(self):
        self.native_exe.write_bytes(b"TAMPERED")
        with self.assertRaisesRegex(BundleRejected,"SHA256 mismatch"):
            package(self.native,self.gui,self.out)
        self.native_exe.write_bytes(self.native_data)
        self.gui_exe.write_bytes(b"TAMPERED")
        with self.assertRaisesRegex(BundleRejected,"SHA256 mismatch"):
            package(self.native,self.gui,self.out)

    def test_wrong_native_checksum_filename_or_missing_gui_checksum_refused(self):
        (self.native/NATIVE_HASH).write_text(self.native_sha+"  unsigned-wallet.exe\n")
        with self.assertRaisesRegex(BundleRejected,"checksum"):
            package(self.native,self.gui,self.out)
        (self.native/NATIVE_HASH).write_text(self.native_sha+"  "+NATIVE_EXE+"\n")
        (self.gui/GUI_HASH).unlink()
        with self.assertRaisesRegex(BundleRejected,"unambiguous"):
            package(self.native,self.gui,self.out)

    def test_duplicate_artifact_rejected_and_source_files_unchanged(self):
        (self.native/"copy").mkdir()
        (self.native/"copy"/NATIVE_EXE).write_bytes(self.native_data)
        with self.assertRaisesRegex(BundleRejected,"unambiguous"):
            package(self.native,self.gui,self.out)

if __name__=="__main__":
    unittest.main()
