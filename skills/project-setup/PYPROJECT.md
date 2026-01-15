# Complete pyproject.toml Reference

## Full Template

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "my-library"
version = "0.1.0"
description = "A concise description of your library"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [
    {name = "Your Name", email = "you@example.com"}
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "ruff>=0.1",
    "mypy>=1.0",
    "pre-commit>=3.0",
]
docs = [
    "sphinx>=7.0",
    "sphinx-rtd-theme>=2.0",
]

[project.urls]
Homepage = "https://github.com/username/my-library"
Documentation = "https://my-library.readthedocs.io"
Repository = "https://github.com/username/my-library"
Changelog = "https://github.com/username/my-library/blob/main/CHANGELOG.md"

[tool.setuptools.packages.find]
where = ["src"]

# Ruff configuration
[tool.ruff]
line-length = 88
target-version = "py310"

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # Pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
]
ignore = ["E501"]

[tool.ruff.lint.isort]
known-first-party = ["my_library"]

# Pytest configuration
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra -q --cov=my_library --cov-report=term-missing"

# MyPy configuration
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

# Coverage configuration
[tool.coverage.run]
branch = true
source = ["src/my_library"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
]
```

## Entry Points

For CLI commands:
```toml
[project.scripts]
mycommand = "my_library.cli:main"
```

For plugins:
```toml
[project.entry-points."my_library.plugins"]
default = "my_library.plugins.default:Plugin"
```

## Build Backends

| Backend | Use Case |
|---------|----------|
| setuptools | Default, C extensions, mature |
| hatchling | Modern pure Python, dynamic version |
| flit | Minimal, simple libraries |
| poetry | Already using Poetry ecosystem |

## Dependency Specifiers

```toml
dependencies = [
    "requests>=2.28",           # Minimum version
    "click~=8.0",               # Compatible (>=8.0, <9.0)
    "numpy>=1.20,<2.0",         # Range
    "legacy!=1.2.3",            # Exclude version
]
```
