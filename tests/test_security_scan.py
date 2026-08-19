import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = (
    Path(__file__).parents[1]
    / "skills"
    / "python"
    / "security-audit"
    / "scripts"
    / "security_scan.py"
)
SPEC = importlib.util.spec_from_file_location("security_scan", SCRIPT)
assert SPEC and SPEC.loader
SECURITY_SCAN = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SECURITY_SCAN
SPEC.loader.exec_module(SECURITY_SCAN)


def result(tool, success=True, findings=None, blocking=0, error=None):
    return SECURITY_SCAN.ScanResult(tool, success, findings or [], blocking, error)


class RunFailureTests(unittest.TestCase):
    """A scanner that cannot launch must be recorded, not raised."""

    def test_missing_scanner_reports_the_install_hint(self):
        with mock.patch.object(SECURITY_SCAN.subprocess, "run", side_effect=FileNotFoundError):
            stdout, err = SECURITY_SCAN._run(["bandit"], "bandit", "uv tool install bandit")

        self.assertIsNone(stdout)
        self.assertFalse(err.success)
        self.assertEqual(err.tool, "bandit")
        self.assertEqual(err.blocking, 0)
        self.assertIn("uv tool install bandit", err.error)

    def test_timed_out_scanner_is_recorded_as_a_failure(self):
        timeout = subprocess.TimeoutExpired(cmd=["semgrep"], timeout=SECURITY_SCAN.SCAN_TIMEOUT)
        with mock.patch.object(SECURITY_SCAN.subprocess, "run", side_effect=timeout):
            stdout, err = SECURITY_SCAN._run(["semgrep"], "semgrep", "uv tool install semgrep")

        self.assertIsNone(stdout)
        self.assertFalse(err.success)
        self.assertEqual(err.blocking, 0)
        self.assertIn("timed out", err.error)


class ReportTests(unittest.TestCase):
    """The console summary must not read as a clean audit when nothing ran."""

    def test_summary_names_the_scanners_that_did_not_run(self):
        report = SECURITY_SCAN.format_report(
            [
                result("bandit", success=False, error="bandit not installed."),
                result("pip-audit"),
                result("semgrep", success=False, error="semgrep timed out after 300s"),
            ]
        )

        self.assertIn("Total findings: 0 (0 blocking)", report)
        self.assertIn("Scanners that did not run: 2 (bandit, semgrep)", report)

    def test_summary_is_quiet_when_every_scanner_ran(self):
        report = SECURITY_SCAN.format_report([result("bandit"), result("pip-audit")])

        self.assertIn("Total findings: 0 (0 blocking)", report)
        self.assertNotIn("did not run", report)


class ExitCodeTests(unittest.TestCase):
    """Exit status is the gate: 0 clean, 1 blocking, 2 a scanner never ran."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.project = Path(self.temp_dir.name).resolve()

    def run_main(self, results, *extra_args):
        argv = ["security_scan.py", str(self.project), *extra_args]
        runners = {
            "run_bandit": "bandit",
            "run_pip_audit": "pip-audit",
            "run_semgrep": "semgrep",
            "check_secrets": "detect-secrets",
        }
        out = io.StringIO()
        original_argv = sys.argv
        sys.argv = argv
        patches = [
            mock.patch.object(SECURITY_SCAN, attr, lambda _p, tool=tool: results[tool])
            for attr, tool in runners.items()
        ]
        try:
            with contextlib.ExitStack() as stack:
                for patch in patches:
                    stack.enter_context(patch)
                with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as raised:
                    SECURITY_SCAN.main()
        finally:
            sys.argv = original_argv
        return raised.exception.code, out.getvalue()

    @staticmethod
    def clean():
        return {
            "bandit": result("bandit"),
            "pip-audit": result("pip-audit"),
            "semgrep": result("semgrep"),
            "detect-secrets": result("detect-secrets"),
        }

    def test_clean_scan_exits_zero(self):
        code, output = self.run_main(self.clean())

        self.assertEqual(code, 0)
        self.assertNotIn("did not run", output)

    def test_blocking_finding_exits_one(self):
        results = self.clean()
        results["bandit"] = result(
            "bandit", findings=[{"issue_text": "eval", "issue_severity": "HIGH"}], blocking=1
        )

        code, _ = self.run_main(results)

        self.assertEqual(code, 1)

    def test_scanner_that_did_not_run_exits_two(self):
        results = self.clean()
        results["semgrep"] = result("semgrep", success=False, error="semgrep not installed.")

        code, output = self.run_main(results)

        self.assertEqual(code, 2)
        self.assertIn("Scanners that did not run: 1 (semgrep)", output)

    def test_blocking_finding_still_wins_over_a_failed_scanner(self):
        results = self.clean()
        results["semgrep"] = result("semgrep", success=False, error="semgrep not installed.")
        results["detect-secrets"] = result(
            "detect-secrets", findings=[{"file": "a.py", "type": "AWS", "line": 3}], blocking=1
        )

        code, _ = self.run_main(results)

        self.assertEqual(code, 1)

    def test_allow_scanner_failure_restores_the_tolerant_exit(self):
        results = self.clean()
        results["semgrep"] = result("semgrep", success=False, error="semgrep not installed.")

        code, output = self.run_main(results, "--allow-scanner-failure")

        self.assertEqual(code, 0)
        self.assertIn("Scanners that did not run: 1 (semgrep)", output)

    def test_skipped_scanner_is_not_a_failure(self):
        results = self.clean()
        results["semgrep"] = result("semgrep", success=False, error="semgrep not installed.")

        code, output = self.run_main(results, "--skip", "semgrep")

        self.assertEqual(code, 0)
        self.assertNotIn("did not run", output)

    def test_json_report_records_the_scanners_that_did_not_run(self):
        results = self.clean()
        results["bandit"] = result("bandit", success=False, error="bandit not installed.")
        report_path = self.project / "report.json"

        code, _ = self.run_main(results, "--output", str(report_path))

        self.assertEqual(code, 2)
        payload = json.loads(report_path.read_text())
        self.assertEqual(payload["scanners_failed"], ["bandit"])
        self.assertEqual(payload["scanner_failures"], 1)


if __name__ == "__main__":
    unittest.main()
