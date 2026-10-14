#!/usr/bin/env python3
"""Deterministic, PUBLIC STATIC-ONLY Hostinger upload ZIP for DEVNIRA website.

The archive contains no RPC backend, coin daemon, private keys, or wallet
seed. It does not upload to Hostinger and cannot activate mainnet.
"""
import argparse
import hashlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

SITE_FILES=("index.html","styles.css","app.js")
STAMP=(2026,10,14,0,0,0)

def create_archive(source:Path, output:Path)->str:
    if source.resolve()==output.resolve() or output.is_dir():
        raise ValueError("Output must be a zip file outside source")
    bodies={}
    for name in SITE_FILES:
        candidate=source / name
        if candidate.is_symlink() or not candidate.is_file():
            raise ValueError("Missing/linked static website file: "+name)
        data=candidate.read_bytes()
        if not data or len(data)>2_000_000:
            raise ValueError("Empty or oversize website file: "+name)
        bodies[name]=data
    html=bodies["index.html"].decode("utf-8")
    if ("NOT mainnet" not in html or "No publicly verified DVN mainnet" not in html
            or 'href="styles.css"' not in html or 'src="app.js"' not in html):
        raise ValueError("Public website disclaimers or assets missing")
    output.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(output,"w",compression=ZIP_DEFLATED,compresslevel=9) as archive:
        for name in SITE_FILES:
            info=ZipInfo(name,STAMP)
            info.compress_type=ZIP_DEFLATED
            info.external_attr=0o100644 << 16
            archive.writestr(info,bodies[name],compress_type=ZIP_DEFLATED,compresslevel=9)
    return hashlib.sha256(output.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--website",type=Path,default=Path("website"))
    parser.add_argument("--output",type=Path,default=Path("devnira-hostinger-static-NOT-MAINNET.zip"))
    args=parser.parse_args()
    checksum=create_archive(args.website,args.output)
    args.output.with_suffix(args.output.suffix+".sha256").write_text(
        checksum+"  "+args.output.name+"\n",encoding="utf-8")
    print(f"STATIC website package (NOT MAINNET): {args.output}")
    print(f"SHA256: {checksum}")

if __name__=="__main__":
    main()
