# Security Scanning in CI

Wires bandit, pip-audit, semgrep, and detect-secrets into continuous integration so every push and pull request is gated on security findings, and keeps dependencies patched.

## Contents

- [GitHub Actions Job](#github-actions-job)
- [Using the Bundled Scan Script](#using-the-bundled-scan-script)
- [Pre-commit Hook for detect-secrets](#pre-commit-hook-for-detect-secrets)
- [Dependabot](#dependabot)
- [Triaging False Positives](#triaging-false-positives)

## GitHub Actions Job

Every tool is installed and run through `uv`, never bare pip. `uv tool install` places each scanner on `PATH`; `uv run` executes them in the project environment.

```yaml
# .github/workflows/security.yml
name: security

on:
  push:
  pull_request:

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Install scanners
        run: uv tool install bandit
          && uv tool install pip-audit
          && uv tool install semgrep
          && uv tool install detect-secrets

      - name: Bandit (static analysis)
        run: uv tool run bandit -r src/ -ll

      - name: pip-audit (dependency CVEs)
        run: uv tool run pip-audit

      - name: Semgrep (SAST)
        run: uv tool run semgrep --config auto --error --quiet src/

      - name: detect-secrets (hardcoded credentials)
        run: uv tool run detect-secrets scan --baseline .secrets.baseline
```

Each step exits non-zero on findings, which fails the job. `bandit -ll` gates on medium+ severity; drop to `-lll` for high-only. `semgrep --error` turns ERROR-severity findings into a non-zero exit.

## Using the Bundled Scan Script

Instead of four separate steps, run all scanners through the script this skill ships. It aggregates findings and exits non-zero when any is blocking (HIGH/CRITICAL bandit, any vulnerable dependency, ERROR-level semgrep, or any secret), so a single step gates the job.

```yaml
      - name: Security scan
        run: uv run python scripts/security_scan.py . --output security-report.json

      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: security-report
          path: security-report.json
```

Skip a scanner that does not apply with `--skip` (choices: `bandit`, `pip-audit`, `semgrep`, `secrets`); for example `--skip semgrep` while tuning rules. The script reports a missing scanner as an error for that tool rather than crashing, so install all four via `uv tool install` first. `if: always()` uploads the JSON even when the scan fails, so findings are inspectable from the run.

## Pre-commit Hook for detect-secrets

Catch secrets before they reach history, not after CI. Create a baseline once, commit it, then wire the hook.

```bash
uv tool install pre-commit
uv tool run detect-secrets scan > .secrets.baseline
```

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: ["--baseline", ".secrets.baseline"]
```

```bash
uv tool run pre-commit install
```

The hook scans staged files and blocks the commit on any secret not already recorded in the baseline. Because it runs on the whole repo the first time, generate the baseline before installing so existing (audited) matches do not block every commit.

## Dependabot

pip-audit reports vulnerable dependencies; Dependabot opens the PRs that fix them. Together they close the loop — the scan fails CI, the update PR resolves it.

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: pip
    directory: "/"
    schedule:
      interval: weekly
    groups:
      dev-dependencies:
        patterns: ["*"]
        dependency-type: development

  - package-ecosystem: github-actions
    directory: "/"
    schedule:
      interval: weekly
```

The `github-actions` ecosystem also keeps the `setup-uv` and action pins in this workflow current. Grouping dev dependencies collapses routine bumps into one PR to cut review noise.

## Triaging False Positives

Suppress only after confirming a finding is genuinely safe, and record why — a bare suppression is indistinguishable from a missed bug.

**bandit — inline `# nosec`:** annotate the exact line, scoped to the specific test ID, with a reason.

```python
# Reviewed: host is validated against ALLOWED_HOSTS above.
subprocess.run(cmd, check=True)  # nosec B603
```

Prefer per-line `# nosec B<id>` over a bare `# nosec` so unrelated new issues on the same line still surface. Project-wide skips belong in `.bandit` (`skips: [B101]`), reserved for rules that never apply to the codebase (for example `B101` assert-used, which is expected in tests).

**semgrep — `# nosemgrep`:** annotate the line, scoped to the rule id.

```python
value = eval(expr)  # nosemgrep: python.lang.security.audit.eval-detected
```

**detect-secrets — the baseline:** a match already in `.secrets.baseline` is treated as reviewed and does not fail. After confirming a flagged string is a false positive (a test fixture, an example key), re-audit the baseline to mark it:

```bash
uv tool run detect-secrets scan --baseline .secrets.baseline
uv tool run detect-secrets audit .secrets.baseline
```

Auditing records the human decision in the baseline; committing the updated baseline is what silences the finding going forward. Never suppress a real secret — rotate it, then remove it from source.

**pip-audit — ignore a specific advisory:** when no fixed version exists yet and the code path is unreachable, pin and ignore the advisory id explicitly rather than disabling the scan.

```bash
uv tool run pip-audit --ignore-vuln GHSA-xxxx-xxxx-xxxx
```

Track each ignored advisory so it can be removed once a patched release ships.
