# Conda Packaging

## PyPI vs conda-forge

Ship to PyPI first — it is the source of truth and most users install with `pip`/`uv`. Add conda-forge when your users live in the conda ecosystem (data science, HPC, GIS) or when your package has non-Python native dependencies (C/C++/Fortran libs, GDAL, CUDA) that conda resolves more cleanly than wheels. A conda-forge recipe almost always builds *from* your PyPI sdist, so PyPI comes first.

Pure-Python libraries with no native deps often do not need conda-forge at all — `pip install` inside a conda env works fine. Reach for conda-forge when native ABI compatibility or the solver matters.

## conda-forge Workflow

conda-forge is community-maintained. You add a package once via a PR to `conda-forge/staged-recipes`; after it merges, a dedicated `<package>-feedstock` repo is created that you co-maintain.

1. Fork/clone `conda-forge/staged-recipes`.
2. Add `recipes/<package>/meta.yaml` (generate it with grayskull, below).
3. Open a PR. CI builds the recipe on Linux/macOS/Windows.
4. A conda-forge member reviews; on merge, the feedstock is auto-created and you are added as a maintainer.

The recipe pins to a released PyPI artifact by URL and `sha256`:

```yaml
package:
  name: my-package
  version: "1.0.0"

source:
  url: https://pypi.io/packages/source/m/my-package/my_package-1.0.0.tar.gz
  sha256: <sha256 of the sdist>

build:
  noarch: python
  script: {{ PYTHON }} -m pip install . -vv
  number: 0

requirements:
  host:
    - python >=3.10
    - pip
    - setuptools >=61
  run:
    - python >=3.10
    - requests >=2.28

test:
  imports:
    - my_package

about:
  home: https://github.com/user/my-package
  license: MIT
  license_file: LICENSE
```

`noarch: python` produces a single cross-platform package — use it for pure-Python libraries. Drop it (and add compilers) only when you build native extensions. The `run` requirements mirror your `pyproject.toml` dependencies; keep them as minimum-version bounds, not exact pins.

## Generating a Recipe with grayskull

Do not hand-write `meta.yaml`. grayskull reads a package's PyPI release and emits a correct recipe with the right URL, sha256, and dependency mapping:

```bash
uv tool run grayskull pypi my-package
```

This writes `my-package/meta.yaml`. Review it (grayskull cannot always infer optional/run deps or license files perfectly), then drop it into `staged-recipes/recipes/`.

## Version Bumps: the Autotick Bot

After the feedstock exists, you rarely touch it for routine releases. When you publish a new version to PyPI, conda-forge's **regro autotick bot** detects it and opens a PR against your feedstock that bumps `version`, updates `sha256`, and resets `build.number` to `0`. If CI is green, merge it — the new conda package builds and uploads automatically.

You only edit the feedstock manually when dependencies change, a build breaks, or you need to bump `build.number` for a rebuild against updated pins (the bot handles the latter for global migrations too).

## pixi and rattler-build

`rattler-build` is the modern, faster reimplementation of `conda-build`; conda-forge is migrating recipes to its `recipe.yaml` format (jinja-free, schema-validated). `pixi` is the modern project/environment manager built on the same Rust `rattler` stack — it resolves conda + PyPI dependencies together and can build packages via `pixi build`. For a new library, developing with pixi and targeting rattler-build is the forward-looking path; the `staged-recipes` + autotick bot flow above remains how you reach conda-forge users regardless of which builder you use locally.
