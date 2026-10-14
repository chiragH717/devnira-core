#!/usr/bin/env python3
"""Package two VERIFIED CI-only DEVNIRA Windows prerelease EXEs for company onboarding.

This is NOT a wallet with sending, secure storage or an active 8-decimal
blockchain. Never include secrets or publish it as mainnet. Inputs MUST be
downloaded from independently checked GitHub Actions run artifacts with
specific immutable provenance and valid per-EXE SHA256 files.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

NATIVE_EXE = "DEVNIRA-Offline-Key-CLI-NOT-MAINNET.exe"
GUI_EXE = "DEVNIRA-Company-Wallet-Setup-NO-SEND.exe"
NATIVE_HASH = "native-cli-sha256.txt"
GUI_HASH = "devnira-windows-readonly-sha256.txt"
NATIVE_RUN = 38599371352
GUI_RUN = 38588478821
NATIVE_SHA = "d307f43daccd81a33e7db5a8ef589cb04d2af6f2"
GUI_SHA = "8a411f107a59fb707b793e9fbb412f1a4545b1eb"
DATE = (2026, 10, 14, 0, 0, 0)

class BundleRejected(ValueError):
    pass

def _one_file(directory: Path, basename: str) -> Path:
    matches = [p for p in directory.rglob(basename) if p.is_file()]
    if len(matches) != 1:
        raise BundleRejected(f"Expected one unambiguous file: {basename}")
    p = matches[0]
    if p.is_symlink() or any(parent.is_symlink() for parent in p.parents
                             if parent != directory.parent):
        raise BundleRejected(f"Symlinked artifact forbidden: {basename}")
    if p.stat().st_size == 0:
        raise BundleRejected(f"Zero length artifact: {basename}")
    return p

def _validated_hash(executable: Path, hash_text: str, name: str) -> str:
    if name == NATIVE_EXE:
        match = re.fullmatch(
            r"([a-f0-9]{64})  DEVNIRA-Offline-Key-CLI-NOT-MAINNET\.exe\s*",
            hash_text, re.ASCII)
    else:
        # PowerShell Get-FileHash | Format-List output from the Windows GUI
        # build. Never trust a digest derived from a differently named file.
        match = re.search(r"(?mi)^\s*Hash\s*:\s*([0-9a-f]{64})\s*$",
                          hash_text)
    if match is None:
        raise BundleRejected(f"Missing or invalid build checksum: {name}")
    recorded = match.group(1).lower()
    with executable.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != recorded:
        raise BundleRejected(f"SHA256 mismatch: {name}")
    return actual

def package(native: Path, gui: Path, output: Path) -> dict:
    native, gui = native.resolve(), gui.resolve()
    if not native.is_dir() or not gui.is_dir():
        raise BundleRejected("Both source artifact directories must exist")
    n=_one_file(native,NATIVE_EXE)
    g=_one_file(gui,GUI_EXE)
    native_checksum=_one_file(native,NATIVE_HASH).read_text(encoding="utf-8")
    gui_checksum=_one_file(gui,GUI_HASH).read_text(encoding="utf-8")
    h_n=_validated_hash(n,native_checksum,NATIVE_EXE)
    h_g=_validated_hash(g,gui_checksum,GUI_EXE)
    data={
        "schema": "devnira-windows-company-wallet-prerelease-bundle-v1",
        "wallet_send_enabled": False,
        "independent_mainnet_active": False,
        "runtime_eight_decimals_activated": False,
        "treasury_10m_minted": False,
        "native_cli": {
            "filename": NATIVE_EXE,
            "sha256": h_n,
            "source_github_run": NATIVE_RUN,
            "source_commit_sha": NATIVE_SHA,
        },
        "company_setup_gui": {
            "filename": GUI_EXE,
            "sha256": h_g,
            "source_github_run": GUI_RUN,
            "source_commit_sha": GUI_SHA,
        },
        "warning": "Unsigned pre-release company wallet preparation only. No Send or live DEVNIRA chain. Independent security audit required before custody.",
    }
    guide = (
        "DEVNIRA WINDOWS COMPANY OFFLINE WALLET - DEVELOPMENT PREVIEW\n"
        "================================================================\n\n"
        "1. This ZIP is NOT a working worldwide DVN transaction wallet.\n"
        "   No production 8-decimal chain, Send or issued treasury coins exist.\n"
        "2. Independently review source, signatures and EXE SHA256 from\n"
        "   manifest.json. Do not trust a checksum solely because it is\n"
        "   packaged with the same executable.\n"
        "3. On your own trusted Windows PC, launch " + GUI_EXE + ".\n"
        "   Select the separately bundled " + NATIVE_EXE + "\n"
        "   under Offline Company Wallet. Paste its trusted SHA256.\n"
        "4. The GUI copies a PowerShell hash-check + native keygen command.\n"
        "   Run it in your PRIVATE interactive PowerShell terminal; do NOT\n"
        "   send seed, mnemonic, private keys, recovery code or password to\n"
        "   ChatGPT, websites, email or GitHub. Back up offline.\n"
        "5. The public SS58-190 address can be prepared for the future\n"
        "   10M DVN treasury (3M liquid + 7M vested monthly) ONLY after\n"
        "   ownership proof, independent runtime genesis and security review.\n"
        "6. Source: https://github.com/chiragH717/devnira-core\n"
        "   WARNING: both executables are UNSIGNED.\n"
    )
    output = output.resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    if output.is_dir() or output in (n.resolve(),g.resolve()):
        raise BundleRejected("Unsafe bundle output path")
    with ZipFile(output, "w", ZIP_DEFLATED, compresslevel=8) as z:
        for name, content in (
            (NATIVE_EXE,n.read_bytes()),
            (GUI_EXE,g.read_bytes()),
            ("manifest.json",(json.dumps(data,indent=2,sort_keys=True)+"\n").encode()),
            ("READ-ME-FIRST.txt",guide.encode()),
        ):
            info=ZipInfo(name, DATE)
            info.compress_type=ZIP_DEFLATED
            info.external_attr=0o100644 << 16
            z.writestr(info,content,compress_type=ZIP_DEFLATED,compresslevel=8)
    with output.open("rb") as stream:
        bundle_sha=hashlib.file_digest(stream,"sha256").hexdigest()
    output.with_name(output.name+".sha256").write_text(
        bundle_sha+"  "+output.name+"\n",encoding="ascii")
    return data

def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--native",type=Path,required=True)
    ap.add_argument("--gui",type=Path,required=True)
    ap.add_argument("--output",type=Path,default=Path("DEVNIRA-Windows-Company-Wallet-Setup-NOT-MAINNET.zip"))
    a=ap.parse_args()
    result=package(a.native,a.gui,a.output)
    print("PASS: Windows offline company wallet development bundle verified")
    print("Native CLI digest:",result["native_cli"]["sha256"])
    print("GUI digest:",result["company_setup_gui"]["sha256"])
    print("NOT a transaction-signing wallet. Real company key must remain on owner's secure device.")

if __name__=="__main__":
    main()
