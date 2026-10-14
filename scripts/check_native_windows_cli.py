#!/usr/bin/env python3
"""Independently assert a patched DEVNIRA Windows binary rejects Quantus mainnet.

The nonzero process exit is EXPECTED and must not be treated as a PowerShell
failure. An unrelated crash, wrong CLI syntax, missing DLL, or unknown option
is NOT proof that the foreign-network chain selector is disabled.

No private keys, mnemonics, network requests, or genesis allocation involved.
"""
import argparse
from pathlib import Path
import subprocess

EXPECTED = "devnira pre-release refuses chain"
MAX_DIAGNOSTIC = 1800


def assert_quantus_mainnet_blocked(executable: Path, *, run=subprocess.run) -> str:
    binary = Path(executable)
    if not binary.is_file():
        raise ValueError("Compiled DEVNIRA native Windows CLI executable required")
    try:
        response = run(
            [str(binary), "--chain", "mainnet", "build-spec"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("Native DEVNIRA CLI cannot execute mainnet isolation test") from exc
    output = (response.stdout or "") + "\n" + (response.stderr or "")
    if response.returncode == 0:
        raise ValueError("SECURITY: native DEVNIRA CLI accepted a foreign Quantus mainnet")
    if EXPECTED not in output.lower():
        raise ValueError(
            "Native CLI did not prove DEVNIRA foreign-network rejection; "
            "its nonzero exit may be an unrelated failure. Diagnostic: "
            + output[:MAX_DIAGNOSTIC]
        )
    return "PASS: native DEVNIRA CLI explicitly rejected Quantus mainnet"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("native_executable", type=Path)
    args = p.parse_args()
    print(assert_quantus_mainnet_blocked(args.native_executable))


if __name__ == "__main__":
    main()
