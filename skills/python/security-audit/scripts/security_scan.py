#!/usr/bin/env python3
"""Run comprehensive security scans on a Python project.

Runs Bandit (static analysis), pip-audit (dependency CVEs), Semgrep (pattern-based
SAST), and detect-secrets (hardcoded credentials), aggregates the findings, and
exits non-zero when any blocking issue is found so it can gate CI.

A scanner that could not run at all — or whose output could not be parsed — is a
gate failure too: exit 1 on blocking findings, exit 2 when a requested scanner
produced no usable result, and 0 only when every requested scanner ran clean. Pass --allow-scanner-failure to tolerate scanners
that could not run.

Usage:
    uv run python scripts/security_scan.py /path/to/project
    uv run python scripts/security_scan.py . --output report.json
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# A scanner that hasn't finished within this window is treated as hung rather
# than blocking the whole run indefinitely.
SCAN_TIMEOUT = 300  # seconds

# Cap per-tool findings printed to the console; the full set still goes to --output.
MAX_FINDINGS_SHOWN = 10

# Raised while reading a scanner's stdout that is not JSON, or is JSON in a
# structure this script cannot walk.
PARSE_ERRORS = (json.JSONDecodeError, AttributeError, TypeError)


@dataclass
class ScanResult:
    tool: str
    success: bool
    findings: list = field(default_factory=list)
    blocking: int = 0
    error: str | None = None


def _run(cmd: list[str], tool: str, install_hint: str, ok_returncodes=(0, 1)):
    """Run a scanner subprocess.

    Returns (stdout, None) on success or (None, ScanResult) describing why the
    tool could not run — so callers never crash on a missing or hung scanner.
    """
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=SCAN_TIMEOUT
        )
    except FileNotFoundError:
        return None, ScanResult(tool, False, error=f"{tool} not installed. Run: {install_hint}")
    except subprocess.TimeoutExpired:
        return None, ScanResult(tool, False, error=f"{tool} timed out after {SCAN_TIMEOUT}s")
    except Exception as e:  # noqa: BLE001 - report any launch failure, don't crash the run
        return None, ScanResult(tool, False, error=str(e))

    if result.returncode not in ok_returncodes:
        return None, ScanResult(
            tool, False, error=result.stderr.strip() or f"exit code {result.returncode}"
        )
    return result.stdout, None


def _unparseable(tool: str, reason: str) -> ScanResult:
    """Record a scanner that ran but emitted output this script cannot consume.

    The reason is the exception's own short message; the scanner's payload is
    never embedded, so a truncated or diagnostic report stays readable.
    """
    return ScanResult(
        tool, False, error=f"{tool} produced output that could not be parsed: {reason}"
    )


def run_bandit(project_path: Path) -> ScanResult:
    """Run Bandit static security analysis. Blocks on HIGH/CRITICAL findings."""
    target = project_path / "src"
    if not target.exists():
        target = project_path

    stdout, err = _run(
        ["bandit", "-r", str(target), "-f", "json"],
        "bandit",
        "uv tool install bandit",
    )
    if err:
        return err

    try:
        data = json.loads(stdout) if stdout else {"results": []}
        findings = data.get("results", [])
        blocking = sum(
            1 for f in findings if f.get("issue_severity", "").upper() in ("HIGH", "CRITICAL")
        )
    except PARSE_ERRORS as e:
        return _unparseable("bandit", str(e))
    return ScanResult("bandit", True, findings, blocking)


def run_pip_audit(project_path: Path) -> ScanResult:
    """Audit the target project's dependencies. Blocks on any vulnerable package."""
    stdout, err = _run(
        ["pip-audit", "--format", "json", str(project_path)],
        "pip-audit",
        "uv tool install pip-audit",
    )
    if err:
        return err

    try:
        data = json.loads(stdout) if stdout else []
        # pip-audit returns either a bare list or {"dependencies": [...]} across versions.
        deps = data.get("dependencies", []) if isinstance(data, dict) else data
        findings = [d for d in deps if d.get("vulns")]
    except PARSE_ERRORS as e:
        return _unparseable("pip-audit", str(e))
    return ScanResult("pip-audit", True, findings, blocking=len(findings))


def run_semgrep(project_path: Path) -> ScanResult:
    """Run Semgrep pattern-based SAST. Blocks on ERROR-severity findings."""
    stdout, err = _run(
        ["semgrep", "--config", "auto", "--json", "--quiet", str(project_path)],
        "semgrep",
        "uv tool install semgrep",
    )
    if err:
        return err

    try:
        data = json.loads(stdout) if stdout else {"results": []}
        findings = data.get("results", [])
        blocking = sum(
            1 for f in findings if f.get("extra", {}).get("severity", "").upper() == "ERROR"
        )
    except PARSE_ERRORS as e:
        return _unparseable("semgrep", str(e))
    return ScanResult("semgrep", True, findings, blocking)


def check_secrets(project_path: Path) -> ScanResult:
    """Check for hardcoded secrets. Any detected secret blocks the run."""
    stdout, err = _run(
        ["detect-secrets", "scan", str(project_path)],
        "detect-secrets",
        "uv tool install detect-secrets",
    )
    if err:
        return err

    try:
        data = json.loads(stdout) if stdout else {"results": {}}
        findings = [
            {"file": file_path, "type": secret.get("type"), "line": secret.get("line_number")}
            for file_path, secrets in data.get("results", {}).items()
            for secret in secrets
        ]
    except PARSE_ERRORS as e:
        return _unparseable("detect-secrets", str(e))
    return ScanResult("detect-secrets", True, findings, blocking=len(findings))


def _describe(finding) -> str:
    """Render a single finding as one line, across the tools' differing shapes."""
    if not isinstance(finding, dict):
        return str(finding)
    if "issue_text" in finding:  # bandit
        return (
            f"[{finding.get('issue_severity', 'UNKNOWN')}] {finding.get('issue_text', '')} "
            f"({finding.get('filename', 'unknown')})"
        )
    if "vulns" in finding:  # pip-audit
        ids = ", ".join(v.get("id", "?") for v in finding.get("vulns", []))
        return f"{finding.get('name')} {finding.get('version', '')}: {ids}"
    if "check_id" in finding:  # semgrep
        path = finding.get("path", "unknown")
        line = finding.get("start", {}).get("line", "?")
        sev = finding.get("extra", {}).get("severity", "INFO")
        return f"[{sev}] {finding.get('check_id')} ({path}:{line})"
    if "file" in finding:  # detect-secrets
        return f"{finding.get('type', 'Secret')} in {finding.get('file')}:{finding.get('line', '?')}"
    return str(finding)


def failed_scanners(results: list[ScanResult]) -> list[str]:
    """Name the requested scanners that could not run (missing, hung, or crashed)."""
    return [result.tool for result in results if not result.success]


def format_report(results: list[ScanResult]) -> str:
    """Format scan results as a readable report."""
    lines = ["=" * 60, "Security Scan Report", "=" * 60, ""]
    total_findings = 0
    total_blocking = 0

    for result in results:
        lines.append(f"## {result.tool.upper()}")
        lines.append("-" * 40)

        if not result.success:
            lines.append(f"Error: {result.error}")
        elif not result.findings:
            lines.append("No issues found.")
        else:
            lines.append(f"Found {len(result.findings)} issue(s), {result.blocking} blocking:")
            for i, finding in enumerate(result.findings[:MAX_FINDINGS_SHOWN], 1):
                lines.append(f"  {i}. {_describe(finding)}")
            if len(result.findings) > MAX_FINDINGS_SHOWN:
                lines.append(f"  ... and {len(result.findings) - MAX_FINDINGS_SHOWN} more")
            total_findings += len(result.findings)
            total_blocking += result.blocking

        lines.append("")

    lines.append("=" * 60)
    lines.append(f"Total findings: {total_findings} ({total_blocking} blocking)")
    failed = failed_scanners(results)
    if failed:
        lines.append(f"Scanners that did not run: {len(failed)} ({', '.join(failed)})")
    lines.append("=" * 60)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Run security scans on a Python project")
    parser.add_argument(
        "project_path",
        type=Path,
        default=Path("."),
        nargs="?",
        help="Path to project (default: current directory)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output JSON report to file",
    )
    parser.add_argument(
        "--skip",
        nargs="+",
        choices=["bandit", "pip-audit", "semgrep", "secrets"],
        default=[],
        help="Skip specific scanners",
    )
    parser.add_argument(
        "--allow-scanner-failure",
        action="store_true",
        help="Exit 0 when a requested scanner could not run (default: exit 2)",
    )

    args = parser.parse_args()
    project_path = args.project_path.resolve()

    if not project_path.exists():
        print(f"Error: Project path does not exist: {project_path}")
        sys.exit(1)

    print(f"Scanning: {project_path}\n")

    scanners = [
        ("bandit", lambda: run_bandit(project_path)),
        ("pip-audit", lambda: run_pip_audit(project_path)),
        ("semgrep", lambda: run_semgrep(project_path)),
        ("secrets", lambda: check_secrets(project_path)),
    ]

    results = []
    for name, runner in scanners:
        if name in args.skip:
            continue
        print(f"Running {name}...")
        results.append(runner())

    print()
    print(format_report(results))

    if args.output:
        report_data = {
            "project": str(project_path),
            "scanners_failed": failed_scanners(results),
            "scanner_failures": len(failed_scanners(results)),
            "results": [
                {
                    "tool": r.tool,
                    "success": r.success,
                    "findings": r.findings,
                    "blocking": r.blocking,
                    "error": r.error,
                }
                for r in results
            ],
        }
        args.output.write_text(json.dumps(report_data, indent=2))
        print(f"\nJSON report saved to: {args.output}")

    # Fail the run if any scanner reported a blocking finding (HIGH/CRITICAL code
    # issues, vulnerable dependencies, ERROR-level SAST hits, or any secret).
    if any(r.blocking for r in results):
        sys.exit(1)
    # A requested scanner that never ran leaves that class of finding unchecked,
    # so it cannot be reported as a clean audit.
    if failed_scanners(results) and not args.allow_scanner_failure:
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
