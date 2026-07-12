#!/usr/bin/env python3
"""Run comprehensive security scans on a Python project.

Runs Bandit (static analysis), pip-audit (dependency CVEs), Semgrep (pattern-based
SAST), and detect-secrets (hardcoded credentials), aggregates the findings, and
exits non-zero when any blocking issue is found so it can gate CI.

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

    data = json.loads(stdout) if stdout else {"results": []}
    findings = data.get("results", [])
    blocking = sum(
        1 for f in findings if f.get("issue_severity", "").upper() in ("HIGH", "CRITICAL")
    )
    return ScanResult("bandit", True, findings, blocking)


def run_pip_audit() -> ScanResult:
    """Run pip-audit for dependency vulnerabilities. Blocks on any vulnerable package."""
    stdout, err = _run(
        ["pip-audit", "--format", "json"],
        "pip-audit",
        "uv tool install pip-audit",
    )
    if err:
        return err

    data = json.loads(stdout) if stdout else []
    # pip-audit returns either a bare list or {"dependencies": [...]} across versions.
    deps = data.get("dependencies", []) if isinstance(data, dict) else data
    findings = [d for d in deps if d.get("vulns")]
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

    data = json.loads(stdout) if stdout else {"results": []}
    findings = data.get("results", [])
    blocking = sum(
        1 for f in findings if f.get("extra", {}).get("severity", "").upper() == "ERROR"
    )
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

    data = json.loads(stdout) if stdout else {"results": {}}
    findings = [
        {"file": file_path, "type": secret.get("type"), "line": secret.get("line_number")}
        for file_path, secrets in data.get("results", {}).items()
        for secret in secrets
    ]
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

    args = parser.parse_args()
    project_path = args.project_path.resolve()

    if not project_path.exists():
        print(f"Error: Project path does not exist: {project_path}")
        sys.exit(1)

    print(f"Scanning: {project_path}\n")

    scanners = [
        ("bandit", lambda: run_bandit(project_path)),
        ("pip-audit", run_pip_audit),
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
    sys.exit(0)


if __name__ == "__main__":
    main()
