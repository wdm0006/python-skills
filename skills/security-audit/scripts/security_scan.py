#!/usr/bin/env python3
"""Run comprehensive security scans on a Python project.

Usage:
    python security_scan.py /path/to/project
    python security_scan.py . --output report.json
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ScanResult:
    tool: str
    success: bool
    findings: list
    error: Optional[str] = None


def run_bandit(project_path: Path) -> ScanResult:
    """Run Bandit static security analysis."""
    try:
        result = subprocess.run(
            ["bandit", "-r", str(project_path / "src"), "-f", "json"],
            capture_output=True,
            text=True,
        )
        if result.returncode in (0, 1):  # 0 = no issues, 1 = issues found
            data = json.loads(result.stdout) if result.stdout else {"results": []}
            return ScanResult(
                tool="bandit",
                success=True,
                findings=data.get("results", []),
            )
        return ScanResult(
            tool="bandit",
            success=False,
            findings=[],
            error=result.stderr,
        )
    except FileNotFoundError:
        return ScanResult(
            tool="bandit",
            success=False,
            findings=[],
            error="bandit not installed. Run: pip install bandit",
        )
    except Exception as e:
        return ScanResult(
            tool="bandit",
            success=False,
            findings=[],
            error=str(e),
        )


def run_pip_audit() -> ScanResult:
    """Run pip-audit for dependency vulnerabilities."""
    try:
        result = subprocess.run(
            ["pip-audit", "--format", "json"],
            capture_output=True,
            text=True,
        )
        if result.returncode in (0, 1):
            data = json.loads(result.stdout) if result.stdout else []
            return ScanResult(
                tool="pip-audit",
                success=True,
                findings=data if isinstance(data, list) else [],
            )
        return ScanResult(
            tool="pip-audit",
            success=False,
            findings=[],
            error=result.stderr,
        )
    except FileNotFoundError:
        return ScanResult(
            tool="pip-audit",
            success=False,
            findings=[],
            error="pip-audit not installed. Run: pip install pip-audit",
        )
    except Exception as e:
        return ScanResult(
            tool="pip-audit",
            success=False,
            findings=[],
            error=str(e),
        )


def run_safety() -> ScanResult:
    """Run Safety for dependency vulnerabilities."""
    try:
        result = subprocess.run(
            ["safety", "check", "--json"],
            capture_output=True,
            text=True,
        )
        if result.stdout:
            data = json.loads(result.stdout)
            vulnerabilities = data.get("vulnerabilities", [])
            return ScanResult(
                tool="safety",
                success=True,
                findings=vulnerabilities,
            )
        return ScanResult(
            tool="safety",
            success=True,
            findings=[],
        )
    except FileNotFoundError:
        return ScanResult(
            tool="safety",
            success=False,
            findings=[],
            error="safety not installed. Run: pip install safety",
        )
    except Exception as e:
        return ScanResult(
            tool="safety",
            success=False,
            findings=[],
            error=str(e),
        )


def check_secrets(project_path: Path) -> ScanResult:
    """Check for hardcoded secrets."""
    try:
        result = subprocess.run(
            ["detect-secrets", "scan", str(project_path)],
            capture_output=True,
            text=True,
        )
        if result.stdout:
            data = json.loads(result.stdout)
            findings = []
            for file_path, secrets in data.get("results", {}).items():
                for secret in secrets:
                    findings.append({
                        "file": file_path,
                        "type": secret.get("type"),
                        "line": secret.get("line_number"),
                    })
            return ScanResult(
                tool="detect-secrets",
                success=True,
                findings=findings,
            )
        return ScanResult(
            tool="detect-secrets",
            success=True,
            findings=[],
        )
    except FileNotFoundError:
        return ScanResult(
            tool="detect-secrets",
            success=False,
            findings=[],
            error="detect-secrets not installed. Run: pip install detect-secrets",
        )
    except Exception as e:
        return ScanResult(
            tool="detect-secrets",
            success=False,
            findings=[],
            error=str(e),
        )


def format_report(results: list[ScanResult]) -> str:
    """Format scan results as a readable report."""
    lines = ["=" * 60, "Security Scan Report", "=" * 60, ""]

    total_findings = 0

    for result in results:
        lines.append(f"## {result.tool.upper()}")
        lines.append("-" * 40)

        if not result.success:
            lines.append(f"Error: {result.error}")
        elif not result.findings:
            lines.append("No issues found.")
        else:
            lines.append(f"Found {len(result.findings)} issue(s):")
            for i, finding in enumerate(result.findings[:10], 1):
                if isinstance(finding, dict):
                    # Bandit format
                    if "issue_text" in finding:
                        lines.append(
                            f"  {i}. [{finding.get('issue_severity', 'UNKNOWN')}] "
                            f"{finding.get('issue_text', 'Unknown issue')}"
                        )
                        lines.append(f"     File: {finding.get('filename', 'unknown')}")
                    # pip-audit format
                    elif "name" in finding:
                        lines.append(
                            f"  {i}. {finding.get('name')} {finding.get('version', '')}: "
                            f"{finding.get('vulns', [])}"
                        )
                    # detect-secrets format
                    elif "file" in finding:
                        lines.append(
                            f"  {i}. {finding.get('type', 'Secret')} in "
                            f"{finding.get('file', 'unknown')}:{finding.get('line', '?')}"
                        )
                    else:
                        lines.append(f"  {i}. {finding}")
                else:
                    lines.append(f"  {i}. {finding}")

            if len(result.findings) > 10:
                lines.append(f"  ... and {len(result.findings) - 10} more")

            total_findings += len(result.findings)

        lines.append("")

    lines.append("=" * 60)
    lines.append(f"Total findings: {total_findings}")
    lines.append("=" * 60)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Run security scans on a Python project"
    )
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
        choices=["bandit", "pip-audit", "safety", "secrets"],
        default=[],
        help="Skip specific scanners",
    )

    args = parser.parse_args()
    project_path = args.project_path.resolve()

    if not project_path.exists():
        print(f"Error: Project path does not exist: {project_path}")
        sys.exit(1)

    print(f"Scanning: {project_path}\n")

    results = []

    if "bandit" not in args.skip:
        print("Running Bandit...")
        results.append(run_bandit(project_path))

    if "pip-audit" not in args.skip:
        print("Running pip-audit...")
        results.append(run_pip_audit())

    if "safety" not in args.skip:
        print("Running Safety...")
        results.append(run_safety())

    if "secrets" not in args.skip:
        print("Checking for secrets...")
        results.append(check_secrets(project_path))

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
                    "error": r.error,
                }
                for r in results
            ],
        }
        args.output.write_text(json.dumps(report_data, indent=2))
        print(f"\nJSON report saved to: {args.output}")

    # Exit with error if any high-severity issues found
    for result in results:
        for finding in result.findings:
            if isinstance(finding, dict):
                severity = finding.get("issue_severity", "").upper()
                if severity in ("HIGH", "CRITICAL"):
                    sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
