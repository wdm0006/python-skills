---
name: packaging-python-libraries
description: Packages and distributes Python libraries using modern pyproject.toml, build backends (setuptools, hatchling), PyPI publishing with trusted publishing, and wheel building. Use when packaging libraries for distribution, publishing to PyPI, or troubleshooting packaging issues.
---

# Python Library Packaging

## pyproject.toml Essentials

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "my-package"
version = "1.0.0"
description = "Short description"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=7.0", "ruff>=0.1", "mypy>=1.0"]

[project.urls]
Homepage = "https://github.com/user/package"
Documentation = "https://package.readthedocs.io"

[project.scripts]
mycli = "my_package.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
```

## Building

```bash
uv build                     # Creates sdist + wheel in dist/
uvx twine check dist/*       # Validate metadata
```

## Publishing to PyPI

Prefer **trusted publishing** from CI (no stored token) — see the CI section
below. For a manual publish, upload with twine via `uvx`:

```bash
uvx twine upload --repository testpypi dist/*  # Test first
uvx twine upload dist/*                         # Production (uses a PyPI token)
```

## GitHub Actions (Trusted Publishing)

Publishing is automated by the canonical tag-triggered release workflow in the
`managing-python-releases` skill — one pipeline builds with `uv` and publishes via
trusted publishing. See **[../release-management/AUTOMATION.md](../release-management/AUTOMATION.md)**;
don't maintain a second copy here.

## Dependency Best Practices

```toml
# DO: Minimum versions
dependencies = ["requests>=2.28", "click>=8.0"]

# DON'T: Exact pins (locks users)
dependencies = ["requests==2.28.1"]

# DO: Optional for features
[project.optional-dependencies]
cli = ["click>=8.0"]
```

## Including Package Data

```toml
[tool.setuptools.package-data]
my_package = ["py.typed", "data/*.json"]
```

```python
from importlib.resources import files
data = files("my_package.data").joinpath("file.json").read_text()
```

For detailed templates, see:
- **[../project-setup/PYPROJECT.md](../project-setup/PYPROJECT.md)** - Complete annotated pyproject.toml (canonical)
- **[CONDA.md](CONDA.md)** - Conda / conda-forge packaging guide

## Verify the Built Artifact (a green build is not a correct wheel)

`uv build` succeeding tells you the backend *ran*, not that the wheel
contains your code. Build backends select files via config — hatchling's
`[tool.hatch.build.targets.wheel]` (`only-include` / `packages` / `include`),
setuptools' `[tool.setuptools.packages.find]`. Get that config wrong and the
backend cheerfully ships a wheel that is missing subpackages or data files, with
no error. `twine check` won't catch it either — it validates metadata, not
contents.

**Always inspect the wheel and install it clean before publishing:**

```bash
uv build
uv run python -m zipfile -l dist/*.whl # list every file the wheel contains
# ^ confirm ALL your subpackages (my_pkg/, my_pkg/sub/) and data files are there,
#   not just the top-level module.
```

The most common footgun is over-narrow file selection. This ships *only*
`server.py` and silently drops the whole `server/` package and `data/`:

```toml
# DON'T — over-narrow include drops everything else
[tool.hatch.build]
only-include = ["server.py"]

# DO — include the package (and any data dirs); let the backend walk it
[tool.hatch.build.targets.wheel]
packages = ["src/my_pkg"]
```

**Name-collision footgun:** never ship both a top-level module `foo.py` and a
package directory `foo/`. The package shadows the module, so `import foo`
resolves to the (often nearly empty) `foo/__init__.py`, and a console entry point
`foo = "foo:main"` fails because that package has no `main`. Pick one — usually
the package — and delete the other.

**Then prove it from a clean install, not from the source tree:**

```bash
uv venv /tmp/verify && uv pip install --python /tmp/verify/bin/python dist/*.whl
cd /tmp && /tmp/verify/bin/python -c "import my_pkg; my_pkg.submodule.real_func"
mycli --help                           # exercise each console script too
```

Run it from a directory *other than the repo root* — otherwise `import my_pkg`
picks up the source tree on `sys.path` and "works" even when the wheel is empty.
And assert on a *real symbol* (`my_pkg.submodule.real_func`), never just that the
bare top-level name imports: `import foo` can succeed against a shadowing empty
package and prove nothing. A CI smoke test that only does `import foo; print("ok")`
is a false green — it passes whether or not the distributed package is usable.

## Checklist

```
Before Release:
- [ ] pyproject.toml valid
- [ ] README.md informative
- [ ] LICENSE file exists
- [ ] Version set correctly
- [ ] twine check passes
- [ ] `uv run python -m zipfile -l dist/*.whl` shows every subpackage + data file
- [ ] No module/package name collision (no foo.py AND foo/)
- [ ] Installed the wheel into a clean venv and imported a real submodule
      symbol from a directory outside the repo (not just the top-level name)
- [ ] Each console script runs after a clean install

After Release:
- [ ] pip install works
- [ ] Import works
- [ ] GitHub release created
```

## Learn More

This skill is based on the [Distribution](https://mcginniscommawill.com/guides/python-library-development/#distribution-reaching-your-users) section of the [Guide to Developing High-Quality Python Libraries](https://mcginniscommawill.com/guides/python-library-development/) by [Will McGinnis](https://mcginniscommawill.com/). See these posts for deeper coverage:

- [pyproject.toml Explained](https://mcginniscommawill.com/posts/2025-01-26-pyproject-toml-explained/)
- [Publishing PyGeohash](https://mcginniscommawill.com/posts/2025-04-06-pygeohash-publishing/)
