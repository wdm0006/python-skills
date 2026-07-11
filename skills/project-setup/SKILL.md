---
name: setting-up-python-libraries
description: Sets up professional Python library projects with modern tooling (pyproject.toml, uv, ruff, pytest, pre-commit, GitHub Actions). Use when creating new Python libraries, modernizing existing projects to pyproject.toml, configuring linting/testing/CI, or setting up Makefiles and pre-commit hooks.
---

# Python Library Project Setup

## Quick Start

Create a new library with this structure:

```
my-library/
├── src/my_library/
│   ├── __init__.py
│   └── py.typed
├── tests/
├── pyproject.toml
├── Makefile
├── .pre-commit-config.yaml
└── .github/workflows/ci.yml
```

Use `src/` layout to prevent accidental imports of development code.

## Core Configuration

For complete templates, see:
- **[PYPROJECT.md](PYPROJECT.md)** - Full pyproject.toml with all tool configs
- **[CI.md](CI.md)** - GitHub Actions and pre-commit setup
- **[MAKEFILE.md](MAKEFILE.md)** - Makefile automation patterns

## Minimal pyproject.toml

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "my-library"
version = "0.1.0"
description = "What it does"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=7.0", "ruff>=0.1", "mypy>=1.0"]

[tool.setuptools.packages.find]
where = ["src"]
```

## Essential Commands

```bash
# Setup
pip install -e ".[dev]"
pre-commit install

# Daily workflow
ruff check src tests        # Lint
ruff format src tests       # Format
pytest                      # Test
mypy src                    # Type check
```

## Keep local checks identical to CI

The most common CI failure is not a bug — it's a check that passes locally but
fails in CI (or vice versa) because the two run different commands. Two rules
prevent an entire class of "green locally, red in CI" (and chronically-red base
branch) problems:

**1. `make lint` must be read-only — never `--fix`.** A `lint` target that runs
`ruff check --fix` mutates your files and almost always exits 0, so pre-existing
violations silently sit on the branch while CI's read-only `ruff check` goes red.
Put `--fix` only in `format` and the pre-commit hook. `make lint` should run the
*exact* commands CI runs.

**2. CI (and `make lint`) must check formatting too.** `ruff check` and
`ruff format` are different tools: the linter passing says nothing about
formatting. Gate on both, or formatting drift ships / turns a branch red
unexpectedly:

```bash
ruff check src tests          # lint rules
ruff format --check src tests # formatting — REQUIRED, not implied by ruff check
```

Lint the **same paths** in the Makefile and CI (add `examples/`, `docs/`, etc. if
they contain Python) — a narrower local scope lets violations accumulate in dirs
CI checks. Configure ruff under `[tool.ruff.lint]` (not the deprecated top-level
`select`/`ignore`), and keep `requires-python` and `[tool.ruff] target-version`
in sync so ruff doesn't apply upgrade rules for a version you don't support.

For coverage, prefer running `pytest --cov` with a terminal report
(`--cov-report=term-missing`) in the CI log over uploading to a third-party
service — no external account, token, or network dependency in the gate.

## Key Decisions

| Choice | Recommendation | Why |
|--------|---------------|-----|
| Layout | `src/` | Catches packaging bugs early |
| Build backend | setuptools | Mature, broad compatibility |
| Linter | ruff | Fast, replaces flake8+isort+black |
| Python range | `>=3.10` | Don't pin exact versions |
| Dependencies | Minimal | Move optional deps to extras |

## Checklist

```
Project Setup:
- [ ] src/ layout with py.typed marker
- [ ] pyproject.toml (not setup.py)
- [ ] Makefile with dev/test/lint/format (lint read-only, no --fix)
- [ ] `make lint` runs the exact `ruff check` + `ruff format --check` CI runs
- [ ] Build-gating tools pinned (linter, formatter, toolchain, test runner) so upstream releases don't flip green/red on unrelated PRs
- [ ] .pre-commit-config.yaml
- [ ] .github/workflows/ci.yml
- [ ] README.md, LICENSE, CHANGELOG.md
- [ ] .gitignore
```

## Helper Script

Create a new project structure:
```bash
python scripts/create_project.py my-library --author "Name"
```

## Learn More

This skill is based on the [Guide to Developing High-Quality Python Libraries](https://mcginniscommawill.com/guides/python-library-development/) by [Will McGinnis](https://mcginniscommawill.com/). See these posts for deeper coverage:

- [Defining Library Scope](https://mcginniscommawill.com/posts/2025-01-17-defining-library-scope/)
- [Dependency Management](https://mcginniscommawill.com/posts/2025-01-21-dependency-management/)
- [Licensing Your Project](https://mcginniscommawill.com/posts/2025-01-24-licensing-your-project/)
- [pyproject.toml Explained](https://mcginniscommawill.com/posts/2025-01-26-pyproject-toml-explained/)
