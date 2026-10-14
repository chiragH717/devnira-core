"""Offline Windows company wallet preparation. NEVER stores or generates secrets.

The native Rust CLI, not this GUI, generates a Dilithium87 keypair on the
company's own trusted Windows machine. A independently SHA256-pinned CLI
executable must be supplied, and the displayed PowerShell command rechecks
the hash just before launch (closing the copy/execute tampering gap).

No real coins, network RPCs, transaction signing, seed input or key storage.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import re

from spec.ss58_company_account import verified_company_public_address
from spec.verify_company_custody import issue_challenge, verify_company_certificate

SHA256 = re.compile(r"^[0-9a-f]{64}$")

class UnsafeWalletExecutable(ValueError):
    pass

def verified_native_wallet_binary(filename: str | Path, trusted_sha256: str) -> Path:
    if not isinstance(trusted_sha256, str) or SHA256.fullmatch(trusted_sha256) is None:
        raise UnsafeWalletExecutable("Independently verified lowercase 64-digit SHA256 is required")
    if not isinstance(filename, (str, Path)) or not str(filename).strip():
        raise UnsafeWalletExecutable("Select the separately compiled DEVNIRA native wallet CLI")
    raw = Path(filename).expanduser()
    if raw.is_symlink():
        raise UnsafeWalletExecutable("Symlinked executable is forbidden")
    try:
        file = raw.resolve(strict=True)
        if not file.is_file() or file.suffix.lower() != ".exe":
            raise UnsafeWalletExecutable("A real native Windows .exe is required")
        # Powershell single-quoted path will be escaped, but control chars can
        # never be passed to a human-pasted command safely.
        if any(ord(x) < 32 for x in str(file)):
            raise UnsafeWalletExecutable("Unsafe character in executable path")
        with file.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
    except OSError as exc:
        raise UnsafeWalletExecutable("Trusted native CLI unavailable") from exc
    if digest != trusted_sha256:
        raise UnsafeWalletExecutable("CLI SHA256 is different from the independently trusted build")
    return file

def _powershell_quoted(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"

def create_offline_keygen_command(filename: str | Path, trusted_sha256: str,
                                   wallet_index: int = 0) -> str:
    """Return only a human-operated offline PowerShell command, never secrets.

    Must be pasted in a trusted local PowerShell terminal with an interactive
    TTY, where the owner alone records mnemonic/recovery data.
    """
    binary=verified_native_wallet_binary(filename,trusted_sha256)
    if type(wallet_index) is not int or not (0 <= wallet_index <= 2**31-1):
        raise UnsafeWalletExecutable("HD wallet index out of range")
    quoted = _powershell_quoted(str(binary))
    return (
        "$dvnExe=" + quoted + "; "
        "$actual=(Get-FileHash -LiteralPath $dvnExe -Algorithm SHA256).Hash.ToLowerInvariant(); "
        "if ($actual -ne '" + trusted_sha256 + "') { throw 'DEVNIRA CLI hash verification failed' }; "
        "& $dvnExe key devnira --scheme standard --wallet-index " + str(wallet_index)
    )

def create_public_ownership_challenge(address: str) -> dict:
    """Generate public-only, nonce-bound 24h challenge; requires NO network."""
    verified_company_public_address(address)
    return issue_challenge(address)

def verify_offline_company_certificate(certificate: dict, filename: str | Path,
                                       trusted_sha256: str) -> dict:
    """Uses trusted native *public* Dilithium signature verification only."""
    binary=verified_native_wallet_binary(filename,trusted_sha256)
    return verify_company_certificate(certificate,binary,trusted_sha256)
