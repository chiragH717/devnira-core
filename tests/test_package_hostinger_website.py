import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from scripts.package_hostinger_website import create_archive, SITE_FILES

ROOT=Path(__file__).resolve().parents[1]

class HostingerWebsitePackageTests(unittest.TestCase):
    def test_deterministic_deployable_root_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/"a.zip"
            b=Path(tmp)/"b.zip"
            self.assertEqual(create_archive(ROOT/"website",a),create_archive(ROOT/"website",b))
            with ZipFile(a) as z:
                self.assertEqual(z.namelist(),list(SITE_FILES))
                index=z.read("index.html").decode("utf-8")
                self.assertIn("NOT mainnet",index)
                self.assertIn("No publicly verified DVN mainnet",index)

    def test_invalid_or_broken_source_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)/"website"
            d.mkdir()
            for name in SITE_FILES:
                (d/name).write_text("test")
            with self.assertRaisesRegex(ValueError,"disclaimers"):
                create_archive(d,Path(tmp)/"out.zip")
            (d/"app.js").unlink()
            with self.assertRaisesRegex(ValueError,"Missing"):
                create_archive(d,Path(tmp)/"out.zip")

if __name__=="__main__":
    unittest.main()
