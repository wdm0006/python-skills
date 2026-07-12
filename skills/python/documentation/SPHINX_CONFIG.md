# Sphinx Configuration

A complete, copy-pasteable Sphinx setup for a Python library: Google-style docstrings via autodoc + napoleon, an autosummary-generated API reference, Markdown support, and ReadTheDocs deployment.

## Contents

- [Dependencies](#dependencies)
- [Directory Layout](#directory-layout)
- [conf.py](#confpy)
- [Root Document (index.md)](#root-document-indexmd)
- [Autosummary API Reference](#autosummary-api-reference)
- [Building Locally](#building-locally)
- [ReadTheDocs (.readthedocs.yaml)](#readthedocs-readthedocsyaml)

## Dependencies

Add a `docs` extra so the toolchain installs with the package:

```toml
[project.optional-dependencies]
docs = [
    "sphinx>=7.0",
    "furo>=2024.0",
    "myst-parser>=2.0",
    "sphinx-copybutton>=0.5",
]
```

Install it with uv:

```bash
uv sync --extra docs
```

## Directory Layout

```
your-package/
├── src/
│   └── yourpackage/
│       └── __init__.py
├── docs/
│   ├── conf.py
│   ├── index.md
│   └── api/
│       └── index.rst
├── .readthedocs.yaml
└── pyproject.toml
```

Keep `docs/` as a sibling of `src/`. The `docs/api/` directory holds the autosummary entry point; generated stub pages land in `docs/api/_autosummary/` (git-ignore it).

## conf.py

```python
import importlib.metadata

project = "yourpackage"
author = "Your Name"
release = importlib.metadata.version("yourpackage")

extensions = [
    "sphinx.ext.autodoc",       # pull docstrings from source
    "sphinx.ext.autosummary",   # generate API stub pages
    "sphinx.ext.napoleon",      # parse Google-style docstrings
    "sphinx.ext.intersphinx",   # cross-link to other projects' docs
    "sphinx.ext.viewcode",      # add "source" links
    "myst_parser",              # write pages in Markdown
    "sphinx_copybutton",        # copy button on code blocks
]

# Google-style only; disable NumPy parsing to avoid ambiguity.
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = False

# Render type hints from signatures into the description, not the signature line.
autodoc_typehints = "description"
autodoc_typehints_description_target = "documented"
autodoc_member_order = "bysource"
autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
}

# Generate autosummary stub pages automatically on each build.
autosummary_generate = True

# Cross-link identifiers to the stdlib and common libraries.
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
}

# Treat both .md (MyST) and .rst as sources.
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

html_theme = "furo"
```

`release` is read from the installed package metadata, so the version never drifts from `pyproject.toml`.

If your package is not installed into the docs environment, autodoc cannot import it. `uv sync --extra docs` installs the project itself, which resolves this; no `sys.path` manipulation is needed for a `src/` layout.

## Root Document (index.md)

MyST lets you author in Markdown while still using Sphinx directives via fenced blocks:

````markdown
# yourpackage

One-line description of the library.

```{toctree}
:maxdepth: 2

api/index
```
````

## Autosummary API Reference

`docs/api/index.rst` lists your top-level modules once; autosummary recurses and writes a page per module, class, and function:

```rst
API Reference
=============

.. autosummary::
   :toctree: _autosummary
   :recursive:

   yourpackage
```

On each build this produces browsable pages for the entire public API from docstrings alone — no per-symbol page to maintain by hand. Add more entries (e.g. `yourpackage.submodule`) only if you want them as separate top-level roots.

## Building Locally

```bash
uv run sphinx-build -b html docs docs/_build/html
```

Add `-W` to turn warnings into errors (recommended for CI, catches broken references and undocumented members):

```bash
uv run sphinx-build -W -b html docs docs/_build/html
```

Open `docs/_build/html/index.html` in a browser. For an auto-reloading dev server, add `sphinx-autobuild` to the `docs` extra and run:

```bash
uv run sphinx-autobuild docs docs/_build/html
```

## ReadTheDocs (.readthedocs.yaml)

ReadTheDocs does not run uv by default, so drive the build explicitly. Install uv, sync the `docs` extra, then invoke `sphinx-build` into the output path RTD expects:

```yaml
version: 2

build:
  os: ubuntu-24.04
  tools:
    python: "3.12"
  jobs:
    install:
      - asdf plugin add uv
      - asdf install uv latest
      - asdf global uv latest
      - uv sync --extra docs
    build:
      html:
        - uv run sphinx-build -W -b html docs $READTHEDOCS_OUTPUT/html

sphinx:
  configuration: docs/conf.py
```

Using `jobs.build.html` overrides RTD's default builder so the docs build with the exact same uv-managed environment as local development. `$READTHEDOCS_OUTPUT/html` is the directory RTD publishes.
