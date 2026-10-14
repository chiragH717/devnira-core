#!/usr/bin/env python3
"""Fail-closed audit of pinned GPU miner SOURCE as a *candidate*, not hardware proof.

No miner authentication tokens, TLS private keys or mining preimages accepted.
Checks the external miner's QPoW Poseidon2 job/nonce implementation and both
real GPU backends without pretending to have run any GPU hardware.
"""
from pathlib import Path
import argparse

REQUIRED = {
    "crates/pow-core/src/lib.rs": [
        "pub use qpow_math::{get_nonce_hash, is_valid_nonce, mine_range};",
        "use qp_poseidon_core::{Goldilocks, Poseidon2};",
    ],
    "crates/engine-cuda/src/kernels/mining.cu": [
        "const u64 P64 = 0xFFFFFFFF00000001ULL;",
        "MAX_HITS",
    ],
    "crates/engine-gpu/src/kernels/mining.wgsl": [
        "Implements Poseidon2 hash function over Goldilocks field",
        "GOLDILOCKS_PRIME_HIGH",
    ],
    "crates/engine-gpu/src/lib.rs": [
        "wgpu::Backends::PRIMARY",
        "wgpu::DeviceType::Cpu",
    ],
    "crates/miner-cli/src/main.rs": [
        "cuda_gpu: bool",
        "gpu_devices: Option<usize>",
        "auth_token_file: Option<PathBuf>",
        "tls_cert_sha256_file: Option<PathBuf>",
        "Command::Benchmark",
    ],
    "crates/miner-service/src/quic.rs": [
        "quantus_miner_api",
        "tls_cert_sha256",
        "auth_token",
    ],
}

def audit(root: Path) -> dict:
    for name, expected in REQUIRED.items():
        content=(root/name).read_text(encoding="utf-8")
        for term in expected:
            if term not in content:
                raise ValueError(f"STOP: upstream GPU miner source drift in {name}: {term}")
    return {
        "source_audit_passed": True,
        "engines": {"nvidia_cuda": "source found; NOT hardware tested",
                    "amd_vulkan_wgpu": "source found; NOT hardware tested"},
        "qpow": "Poseidon2 and qpow-math source present, not DEVNIRA consensus proof",
        "real_gpu_pow_proven": False,
        "two_node_dvn_network_proven": False,
        "protocol_integration_test_passed": False,
        "reproducible": "requires config/upstream-pins.json sha verification",
    }

if __name__ == "__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("miner_root",type=Path)
    args=ap.parse_args()
    import json
    print(json.dumps(audit(args.miner_root),indent=2))
