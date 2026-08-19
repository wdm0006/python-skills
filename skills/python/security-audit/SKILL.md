---
name: auditing-python-security
description: Audits Python libraries for security vulnerabilities using Bandit, pip-audit, Semgrep, and detect-secrets. Identifies SQL injection, command injection, hardcoded credentials, secrets exposed through tracebacks, weak cryptography, and insecure deserialization. Use when reviewing library security, setting up security scanning in CI, or implementing secure coding patterns.
---

# Python Security Auditing

## Quick Start

```bash
# Run all four scanners (gates CI): exit 1 on a blocking finding, exit 2 when a
# requested scanner could not run, exit 0 only when every scanner ran clean:
uv run python scripts/security_scan.py .

# Tolerate scanners that are missing or hung (restores exit 0 in that case):
uv run python scripts/security_scan.py . --allow-scanner-failure

# Or individually:
uvx bandit -r src/ -ll                       # High-severity static analysis
uvx pip-audit .                              # This project's dependencies
uvx semgrep --config auto src/               # Pattern-based SAST
uvx detect-secrets scan > .secrets.baseline  # Secrets detection
```

## Tool Configuration

**Bandit (.bandit):**
```yaml
exclude_dirs: [tests/, docs/, .venv/]
skips: [B101]  # assert_used - OK in tests
```

**pip-audit:**
```bash
uvx pip-audit -r requirements.txt     # Scan requirements
uvx pip-audit --fix                   # Auto-fix vulnerabilities
```

## Common Vulnerabilities

| Issue | Bandit ID | Fix |
|-------|-----------|-----|
| SQL injection | B608 | Use parameterized queries |
| Command injection | B602 | subprocess without shell=True |
| Hardcoded secrets | B105, B106 | Environment variables |
| Weak crypto | B303 | Use SHA-256+, bcrypt for passwords |
| Pickle untrusted data | B301 | Use JSON instead |
| Path traversal | B108 | Validate with Path.resolve() |

## Secure Patterns

```python
# SQL - Parameterized query
conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))

# Commands - No shell
subprocess.run(["cat", filename], check=True)

# Secrets - Environment
API_KEY = os.environ.get("API_KEY")

# Paths - Validate
base = Path("/data").resolve()
file_path = (base / filename).resolve()
if not file_path.is_relative_to(base):
    raise ValueError("Invalid path")
```

## Tracebacks Must Not Dump Frame Locals

Rich exception renderers can print every local variable in every stack frame.
That turns an ordinary unhandled exception into a credential leak: API tokens,
authorization headers, request bodies, and decrypted configuration commonly live
in locals when the traceback is rendered to a terminal or CI log.

Keep local-variable rendering disabled anywhere logs can leave the developer's
machine:

```python
from rich.traceback import install

install(show_locals=False)
```

Do not stop at asserting the configuration call. Exercise the installed exception
hook with a sentinel secret and inspect the rendered output. This catches a later
refactor that replaces the hook or re-enables locals elsewhere:

```python
import sys


def test_unhandled_traceback_does_not_expose_locals(capsys):
    sentinel = "sentinel-secret-that-must-not-appear"

    try:
        raise RuntimeError("boom")
    except RuntimeError:
        exc_type, exc, traceback = sys.exc_info()
        sys.excepthook(exc_type, exc, traceback)

    output = capsys.readouterr()
    rendered = output.out + output.err
    assert "RuntimeError: boom" in rendered  # proves the hook rendered
    assert sentinel not in rendered
```

Use a unique sentinel, never a real credential. Assert both that the exception was
rendered and that the sentinel was absent; an empty or bypassed output path must
not make the security test pass vacuously.

## CI Integration

```yaml
# .github/workflows/security.yml — full workflow in CI_SECURITY.md
- uses: astral-sh/setup-uv@v5
- run: uv run python scripts/security_scan.py . --output security-report.json
```

For detailed patterns, see:
- **scripts/security_scan.py** — runs all four scanners and exits non-zero on blocking findings (exit 1) or on a requested scanner that could not run (exit 2, opt out with `--allow-scanner-failure`) (`uv run python scripts/security_scan.py .`)
- **[VULNERABILITIES.md](VULNERABILITIES.md)** - Vulnerability classes with vulnerable→fixed pairs
- **[CI_SECURITY.md](CI_SECURITY.md)** - Complete CI workflow, pre-commit, Dependabot, triage

## Audit Checklist

```
Code:
- [ ] No SQL injection (parameterized queries)
- [ ] No command injection (no shell=True)
- [ ] No hardcoded secrets
- [ ] Exception and logging configuration cannot render frame locals containing secrets
- [ ] No weak crypto (MD5/SHA1)
- [ ] Input validation on external data
- [ ] Path traversal prevention
- [ ] SSRF fetches connect to the validated IP on every redirect hop (DNS rebinding safe)
- [ ] SSRF deny policy covers IPv4/IPv6 and CGNAT (`100.64.0.0/10`)

Dependencies:
- [ ] pip-audit clean
- [ ] Minimal dependencies
- [ ] From trusted sources

CI:
- [ ] Security scan on every PR
- [ ] Weekly dependency scan
```

## Learn More

This skill is based on the [Security](https://mcginniscommawill.com/guides/python-library-development/#security-a-matter-of-trust) section of the [Guide to Developing High-Quality Python Libraries](https://mcginniscommawill.com/guides/python-library-development/) by [Will McGinnis](https://mcginniscommawill.com/). See these posts for deeper coverage:

- [Avoiding Injection Flaws](https://mcginniscommawill.com/posts/2025-01-18-avoiding-injection-flaws/)
- [Intro to Bandit](https://mcginniscommawill.com/posts/2025-01-25-intro-to-bandit/)
- [Advanced Bandit Configuration](https://mcginniscommawill.com/posts/2025-08-22-advanced-bandit-configuration/)
- [SQL Injection Detection](https://mcginniscommawill.com/posts/2025-08-25-sql-injection-detection-b608/)
- [Dependency Security with pip-audit](https://mcginniscommawill.com/posts/2025-01-27-dependency-security-pip-audit/)
- [Handling Sensitive Data](https://mcginniscommawill.com/posts/2025-01-29-handling-sensitive-data/)
- [Secure Coding Practices](https://mcginniscommawill.com/posts/2025-02-02-secure-coding-practices/)
