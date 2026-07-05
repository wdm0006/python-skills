# CI/CD Configuration Reference

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

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install uv
        uses: astral-sh/setup-uv@v1

      - name: Install dependencies
        run: uv pip install --system -e ".[dev]"

      - name: Lint
        run: |
          ruff check src tests
          ruff format --check src tests   # formatting is a separate gate from ruff check

      - name: Type check
        run: mypy src

      - name: Test
        run: pytest --cov=src --cov-report=term-missing
```

Run the **same** `ruff check` + `ruff format --check` commands here that `make
lint` runs — if they diverge, a branch that passes locally goes red in CI (or
vice versa). Lint the same paths, too (add `examples/`/`docs/` if they hold
Python).

Coverage is reported in the job log via `--cov-report=term-missing` rather than
uploaded to a third-party service — no external account, token, or network
dependency in the gate. If you later want an XML/HTML artifact, add
`--cov-report=xml` and store it as a build artifact instead of uploading it.

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

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags: ['v*']

jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install build
      - run: python -m build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

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
