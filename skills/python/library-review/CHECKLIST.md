# Full Review Checklist

The detailed expansion of the "Best Practices Checklist" in SKILL.md. Work through each dimension in order. Run the listed command from the repository root and record the result as evidence in your report. Commands assume a `src/` layout with the import package at `src/package/`; adjust the path to the actual package name.

## Contents

- [Structure](#structure)
- [Packaging](#packaging)
- [Code Quality](#code-quality)
- [Testing](#testing)
- [Security](#security)
- [Documentation](#documentation)
- [API Design](#api-design)
- [CI/CD](#cicd)

## Structure

- [ ] `src/` layout in use (import package lives under `src/`, not the repo root) — `ls src/`
- [ ] Single, clearly named import package matching the distribution name
- [ ] `py.typed` marker present so type hints ship to consumers — `ls src/package/py.typed`
- [ ] Tests live outside the import package in a top-level `tests/` directory — `ls tests/`
- [ ] `LICENSE` file present at the repo root — `ls LICENSE`
- [ ] `README` present at the repo root — `ls README*`
- [ ] `CHANGELOG` present and dated — `ls CHANGELOG*`
- [ ] No stray build artifacts committed (`build/`, `dist/`, `*.egg-info/`, `__pycache__/`)
- [ ] `.gitignore` covers Python artifacts and virtualenvs

## Packaging

- [ ] `pyproject.toml` is the single source of build config; no `setup.py`/`setup.cfg` carrying metadata — `ls pyproject.toml setup.py 2>/dev/null`
- [ ] Standards-based build backend declared under `[build-system]` (hatchling, flit, setuptools, or pdm)
- [ ] Core metadata complete: `name`, `version`, `description`, `readme`, `license`, `authors`, `requires-python`
- [ ] Runtime dependencies use lower-bound / compatible-release ranges, not exact `==` pins
- [ ] Optional extras grouped under `[project.optional-dependencies]`; dev tooling separated from runtime deps
- [ ] Package builds cleanly — `uv build`
- [ ] Built artifacts pass metadata validation — `uv run twine check dist/*`
- [ ] Wheel contains `py.typed` and no test or fixture files — `unzip -l dist/*.whl`
- [ ] Version is defined in exactly one place (static field or a single dynamic source)

## Code Quality

- [ ] Type hints on all public functions, methods, and class attributes
- [ ] Static type check passes — `uv run mypy src/`
- [ ] Lint passes with no errors — `uv run ruff check src/`
- [ ] Formatting is consistent — `uv run ruff format --check src/`
- [ ] Public functions and classes have docstrings
- [ ] No bare `except:` clauses; exceptions are specific and re-raised or handled deliberately
- [ ] No mutable default arguments
- [ ] No wildcard imports (`from x import *`)
- [ ] Public API is explicit via `__all__` in the top-level `__init__.py`
- [ ] No dead code, commented-out blocks, or debug `print` statements
- [ ] Logging uses the `logging` module, not `print`

## Testing

- [ ] Tests exist and are collectable — `uv run pytest --collect-only`
- [ ] Full suite passes — `uv run pytest`
- [ ] Coverage is at least 85% and enforced — `uv run pytest --cov=package --cov-report=term-missing --cov-fail-under=85`
- [ ] Edge cases and error paths are exercised, not just the happy path
- [ ] Tests are isolated (no shared mutable state, no ordering dependencies, no reliance on network or wall-clock time)
- [ ] Fixtures used for setup instead of duplicated boilerplate
- [ ] Parametrization used for input matrices rather than copy-pasted test bodies
- [ ] Public behavior is tested against the public API, not private internals
- [ ] Test names describe the behavior under test

## Security

- [ ] No hardcoded secrets, tokens, or credentials — `uv run detect-secrets scan`
- [ ] Static security scan is clean — `uv run bandit -r src/`
- [ ] Dependencies have no known vulnerabilities — `uv run pip-audit`
- [ ] External and user-supplied input is validated before use
- [ ] No use of `eval`, `exec`, `pickle` on untrusted data, or `subprocess` with `shell=True` on untrusted input
- [ ] No overly permissive file permissions or predictable temp-file paths
- [ ] Cryptography uses vetted libraries, never hand-rolled primitives
- [ ] A security contact or disclosure policy is documented — `ls SECURITY*`

## Documentation

- [ ] `README` covers what the library does, install, and a minimal runnable usage example
- [ ] Install instructions are current and copy-pasteable
- [ ] Public API is documented (docstrings, a rendered API reference, or both)
- [ ] `CHANGELOG` is maintained and follows a consistent, dated format
- [ ] `LICENSE` matches the license declared in `pyproject.toml`
- [ ] Contributing guide present for external contributors — `ls CONTRIBUTING*`
- [ ] Examples in the docs actually run against the current version
- [ ] Supported Python versions are stated and match `requires-python`

## API Design

- [ ] Naming is consistent (snake_case functions, PascalCase classes) and follows PEP 8
- [ ] Public surface is minimal and intentional; internals are underscore-prefixed
- [ ] Default argument values are sensible and safe for the common case
- [ ] Functions do one thing; parameter lists are short or use keyword-only arguments for clarity
- [ ] Errors are raised as specific, documented exception types
- [ ] Return types are consistent (no returning different shapes from the same function)
- [ ] Backward compatibility is respected; deprecations use warnings before removal
- [ ] Semantic versioning is followed for breaking changes

## CI/CD

- [ ] CI configuration present — `ls .github/workflows/ 2>/dev/null`
- [ ] Tests run automatically on pull requests
- [ ] CI runs against the full matrix of supported Python versions
- [ ] Lint, format, and type checks run in CI, not just tests
- [ ] Security scanning (`bandit`, `pip-audit`) runs in CI
- [ ] Coverage is measured in CI and fails below the 85% threshold
- [ ] Releases are automated (tag-triggered publish to PyPI)
- [ ] Build artifacts are validated before publish — `uv run twine check dist/*`
- [ ] CI is currently green on the default branch
