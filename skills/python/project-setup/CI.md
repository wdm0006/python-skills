# CI/CD Configuration Reference

## Contents
- GitHub Actions CI (lint, type-check, test matrix)
- Pin your CI tooling
- Pre-commit configuration
- Release workflow (points to the release-management skill)
- .gitignore

## GitHub Actions CI

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Set up Python ${{ matrix.python-version }}
        run: uv python install ${{ matrix.python-version }}

      - name: Install dependencies
        run: uv sync --extra dev --python ${{ matrix.python-version }}

      - name: Lint
        run: |
          uv run ruff check src tests
          uv run ruff format --check src tests   # formatting is a separate gate from ruff check

      - name: Type check
        run: uv run mypy src

      - name: Test
        run: uv run pytest --cov=src --cov-report=term-missing
```

Run the **same** `ruff check` + `ruff format --check` commands here that `make
lint` runs — if they diverge, a branch that passes locally goes red in CI (or
vice versa). Lint the same paths, too (add `examples/`/`docs/` if they hold
Python).

Coverage is reported in the job log via `--cov-report=term-missing` rather than
uploaded to a third-party service — no external account, token, or network
dependency in the gate. If you later want an XML/HTML artifact, add
`--cov-report=xml` and store it as a build artifact instead of uploading it.

## Pin your CI tooling — don't let upstream releases decide green/red

Identical local and CI *commands* still aren't reproducible if CI installs the
tools at "latest." When a linter, formatter, language toolchain, test
orchestrator, or floated runtime dependency auto-upgrades, your pass/fail can
flip on a PR that never touched the affected code — green/red becomes a function
of upstream release dates, not your diff. These failure modes all recur:

- **Formatter version drift.** A formatter installed at latest can reformat files
  under a newer release, so a PR that never touched those files fails the
  `--check` gate (or a version bump silently reformats them). Pin the formatter to
  one version and use that *same* version locally and in the pre-commit hook.
- **Linter config schema tied to the linter's major version.** When the installed
  linter's major version and the config file's schema drift apart, the linter
  fails at config validation *before it lints a single line* — a red job with no
  real violation. Pin the linter/action major version to match the config schema
  (and bump both together).
- **A floated runtime dependency your tests import.** A `latest` numeric/plotting/
  framework dependency can deprecate-then-remove an API between releases, turning
  even a docs-only PR red. Pin such deps (or a compatible range), or at minimum
  know which ones float so a surprise red isn't mistaken for your change.
- **Auto-upgrading language toolchains.** A toolchain resolver that fetches a
  newer version than your build matrix *declares* means the matrix tests a version
  it never names — the coverage you advertise is fiction. Pin the toolchain and
  the matrix to the project's declared minimum so the matrix tests what it claims.
- **Test-orchestrator default changes.** An unpinned test runner or orchestrator
  can change a default between minor versions (e.g. a missing interpreter flipping
  from "skip" to "hard fail"), reddening an unrelated PR. Pin it, and set the
  behavior explicitly in config rather than relying on the default.

### Tox: make missing-interpreter behavior explicit

A tox envlist does not install those Python versions. If the runner provides only
Python 3.12 while tox declares `py310,py311,py312`, the result depends on tox's
missing-interpreter policy — and relying on its current default makes unrelated
tool upgrades capable of breaking CI.

Choose one owner for the version matrix:

- **GitHub Actions owns it (preferred):** install one matrix Python per job and
  run only that matching tox environment.
- **Tox owns it:** install every declared interpreter before invoking tox.
- **A single-interpreter job intentionally runs what is available:** opt into
  skipping explicitly so a tox upgrade cannot change the contract.

```ini
# tox.ini, or legacy_tox_ini in pyproject.toml
[tox]
envlist = py310,py311,py312
skip_missing_interpreters = true
```

Do not use `skip_missing_interpreters = true` to pretend an uninstalled version
was tested. The CI log and status checks must still make the actual coverage
obvious; for a supported-version gate, install every version or use an Actions
matrix.

Rule of thumb: pin every tool that gates the build (linter, formatter, type
checker, toolchain, test runner) to an explicit version, and bump them in their
own dedicated PR — so a tooling bump's fallout lands in a diff that's *about* the
bump, not scattered across unrelated feature PRs.

## Pre-commit Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: []
```

## Release Workflow

The tag-triggered PyPI publish workflow (trusted publishing, GitHub release, and
the release runbook) is owned by the `managing-python-releases` skill (see its
AUTOMATION.md reference). Keep one copy there rather than a second `release.yml` here.

## .gitignore

```gitignore
__pycache__/
*.py[cod]
*.so
build/
dist/
*.egg-info/
.venv/
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/
.ruff_cache/
.idea/
.vscode/
.DS_Store
```
