#!/usr/bin/env python3
"""Read actual PCI/DRM GPU hardware in a LOCAL Linux miner host.

This is device presence/driver evidence, NOT valid QPoW nonce, payout, or
reproducible GPU mining. Never claim hardware based on miner source or CI
runners that have no physical NVIDIA/AMD device.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Sequence

class GpuHardwareMissing(ValueError):pass

VENDORS={"0x10de":"NVIDIA","0x1002":"AMD"}
REQUIRED_DRIVER={"NVIDIA":("nvidia",),"AMD":("amdgpu",)}
MAX_DEVICES=32
NAME=re.compile(r"[A-Za-z0-9_.+-]{1,64}\Z")

def scan(root:Path=Path("/sys/class/drm"))->dict:
    if root.is_symlink() or not root.is_dir():
        raise GpuHardwareMissing("No local Linux DRM sysfs; physical GPU validation unavailable")
    devices=[]
    seen=set()
    for card in sorted(root.glob("card[0-9]*")):
        if not re.fullmatch(r"card[0-9]{1,2}",card.name):
            continue
        device=card/"device"
        if not device.exists():
            continue
        try:
            vendor=(device/"vendor").read_text(encoding="ascii").strip().lower()
            if vendor not in VENDORS:
                continue
            identity=device.resolve(strict=True)
            if identity in seen:continue
            seen.add(identity)
            driver=(device/"driver").resolve(strict=True).name
            if driver not in REQUIRED_DRIVER[VENDORS[vendor]]:
                raise GpuHardwareMissing("Physical GPU driver unavailable, refused CPU/fallback device")
            pci=identity.name
            if not NAME.fullmatch(pci):
                raise GpuHardwareMissing("Unsafe PCI device ID")
            serial=(vendor+"|"+pci+"|"+driver).encode()
            devices.append({"vendor":VENDORS[vendor],"pci_device_sha256":sha256(serial).hexdigest(),
                            "kernel_driver":driver,"physical_drm_device":True})
        except (OSError,UnicodeError) as exc:
            raise GpuHardwareMissing("Unreadable actual physical GPU/driver") from exc
    if len(devices)>MAX_DEVICES:
        raise GpuHardwareMissing("Unusually large GPU enumeration requires review")
    counts={vendor:sum(d["vendor"]==vendor for d in devices) for vendor in ("NVIDIA","AMD")}
    return {"schema":"dvn-linux-real-gpu-device-presence-v1",
            "gpu_devices":devices,"physical_vendor_count":counts,
            "actual_qpow_nonce_verified":False,"reward_finality_verified":False,
            "network_pool_payout_verified":False,"mainnet_ready":False}

def require(gpus:dict,*,nvidia:bool,amd:bool)->dict:
    counts=gpus["physical_vendor_count"]
    if nvidia and counts.get("NVIDIA",0)<1:
        raise GpuHardwareMissing("Physical NVIDIA GPU/driver absent; CUDA test cannot be certified")
    if amd and counts.get("AMD",0)<1:
        raise GpuHardwareMissing("Physical AMD GPU/driver absent; Vulkan QPoW cannot be certified")
    return gpus

def main():
    p=argparse.ArgumentParser(description="Real physical GPU presence only; no mining simulation")
    p.add_argument("--drm-root",type=Path,default=Path("/sys/class/drm"))
    p.add_argument("--require-nvidia",action="store_true")
    p.add_argument("--require-amd",action="store_true")
    p.add_argument("--json-out",type=Path,required=True)
    a=p.parse_args()
    report=require(scan(a.drm_root),nvidia=a.require_nvidia,amd=a.require_amd)
    if a.json_out.exists() or a.json_out.is_symlink():
        p.exit(2,"STOP: refusing overwrite of GPU hardware observation\n")
    a.json_out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("REAL local GPU drivers detected. QPoW and mining payouts STILL UNVERIFIED.")
if __name__=="__main__":main()
