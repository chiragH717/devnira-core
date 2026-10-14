"""A deliberately rejected foreign chain is a PASS only for the right reason."""
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest

from scripts.check_native_windows_cli import assert_quantus_mainnet_blocked


class NativeWindowsMainnetGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.binary = Path(self.tmp.name) / "test-devnira.exe"
        self.binary.write_bytes(b"FAKE TEST BINARY, NOT A REAL NATIVE KEY GENERATOR")

    def execute(self, status: int, stdout: str = "", stderr: str = "") -> str:
        calls = []

        def run(args, **kwargs):
            calls.append((args, kwargs))
            return SimpleNamespace(returncode=status, stdout=stdout, stderr=stderr)

        verdict = assert_quantus_mainnet_blocked(self.binary, run=run)
        self.assertEqual(calls[0][0], [str(self.binary), "build-spec", "--chain", "mainnet"])
        self.assertFalse(calls[0][1]["check"])
        self.assertTrue(calls[0][1]["capture_output"])
        return verdict

    def test_expected_foreign_chain_rejection_is_success(self):
        self.assertIn(
            "PASS", self.execute(1, stderr="Error: DEVNIRA pre-release refuses chain 'mainnet'")
        )

    def test_acceptance_is_a_security_failure_even_if_stdout_mentions_refusal(self):
        with self.assertRaisesRegex(ValueError, "accepted a foreign"):
            self.execute(0, stdout="DEVNIRA pre-release refuses chain")

    def test_arbitrary_compilation_crash_or_cli_error_does_not_count(self):
        for message in ("error: unrecognized option --chain",
                        "DLL not found", "panic: out of memory", ""):
            with self.subTest(error=message):
                with self.assertRaisesRegex(ValueError, "did not prove"):
                    self.execute(1, stderr=message)

    def test_expected_phrase_must_be_actual_cli_diagnostic(self):
        with self.assertRaisesRegex(ValueError, "did not prove"):
            self.execute(1, stderr="Failed, but no specific foreign-chain refusal")

    def test_missing_binary_and_execution_failure_rejected(self):
        with self.assertRaisesRegex(ValueError, "executable required"):
            assert_quantus_mainnet_blocked(Path(self.tmp.name) / "missing.exe")

        def broken(*args, **kwargs):
            raise OSError("native binary load failed")

        with self.assertRaisesRegex(ValueError, "cannot execute"):
            assert_quantus_mainnet_blocked(self.binary, run=broken)

    def test_timeout_rejected(self):
        def timedout(*args, **kwargs):
            raise subprocess.TimeoutExpired("native", 90)

        with self.assertRaisesRegex(ValueError, "cannot execute"):
            assert_quantus_mainnet_blocked(self.binary, run=timedout)


if __name__ == "__main__":
    unittest.main()
