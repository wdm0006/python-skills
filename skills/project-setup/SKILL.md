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
- [ ] Makefile with dev/test/lint/format
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
