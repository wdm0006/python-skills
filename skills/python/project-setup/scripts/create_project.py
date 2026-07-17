#!/usr/bin/env python3
"""Create a new Python library project with modern best practices.

Usage:
    uv run python scripts/create_project.py my-library
    uv run python scripts/create_project.py my-library --author "Your Name" --email you@example.com
"""

import argparse
import json
import keyword
import re
import sys
from datetime import date, datetime
from pathlib import Path
from textwrap import dedent


def _package_name(distribution_name: str) -> str:
    package_name = re.sub(r"[-_.]+", "_", distribution_name).lower()
    if not package_name.isidentifier() or keyword.iskeyword(package_name):
        raise ValueError(
            f"Project name {distribution_name!r} does not produce a valid Python "
            f"package name ({package_name!r})"
        )
    return package_name


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def create_project(
    name: str,
    author: str = "Your Name",
    email: str = "you@example.com",
    description: str = "A Python library",
) -> Path:
    """Create a new Python library project structure."""
    package_name = _package_name(name)
    project_dir = Path(name)

    if project_dir.exists():
        raise ValueError(f"Directory {name} already exists")

    # Create directory structure
    dirs = [
        project_dir / "src" / package_name,
        project_dir / "tests",
        project_dir / "docs",
        project_dir / ".github" / "workflows",
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Create pyproject.toml
    pyproject = dedent(f'''
        [build-system]
        requires = ["setuptools>=61.0", "wheel"]
        build-backend = "setuptools.build_meta"

        [project]
        name = {_toml_string(name)}
        version = "0.1.0"
        description = {_toml_string(description)}
        readme = "README.md"
        requires-python = ">=3.10"
        license = {{text = "MIT"}}
        authors = [
            {{name = {_toml_string(author)}, email = {_toml_string(email)}}}
        ]
        classifiers = [
            "Development Status :: 3 - Alpha",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: MIT License",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: 3.12",
            "Programming Language :: Python :: 3.13",
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

        [project.urls]
        Homepage = {_toml_string(f"https://github.com/username/{name}")}
        Repository = {_toml_string(f"https://github.com/username/{name}")}

        [tool.setuptools.packages.find]
        where = ["src"]

        [tool.ruff]
        line-length = 88
        target-version = "py310"

        [tool.ruff.lint]
        select = ["E", "W", "F", "I", "B", "C4", "UP"]

        [tool.pytest.ini_options]
        testpaths = ["tests"]
        addopts = "-ra -q --cov={package_name}"

        [tool.mypy]
        python_version = "3.10"
        warn_return_any = true
        disallow_untyped_defs = true

        [tool.coverage.run]
        branch = true
        source = ["src/{package_name}"]
    ''').strip()

    (project_dir / "pyproject.toml").write_text(pyproject)

    # Create __init__.py
    init_py = dedent(f'''
        {f"{description}."!r}

        __version__ = "0.1.0"
    ''').strip()

    (project_dir / "src" / package_name / "__init__.py").write_text(init_py + "\n")

    # Create py.typed marker
    (project_dir / "src" / package_name / "py.typed").write_text("")

    # Create test file
    test_init = dedent(f'''
        """Tests for {package_name}."""

        import {package_name}


        def test_version():
            """Test version is defined."""
            assert {package_name}.__version__
    ''').strip()

    (project_dir / "tests" / "__init__.py").write_text("")
    (project_dir / "tests" / f"test_{package_name}.py").write_text(test_init + "\n")

    # Create README
    readme = dedent(f'''
        # {name}

        {description}

        ## Installation

        ```bash
        uv add {name}
        ```

        ## Quick Start

        ```python
        import {package_name}

        # Your code here
        ```

        ## Development

        ```bash
        # Clone repository
        git clone https://github.com/username/{name}
        cd {name}

        # Install in development mode
        uv sync --extra dev

        # Run tests
        uv run pytest

        # Run linting
        uv run ruff check src tests
        ```

        ## License

        MIT License
    ''').strip()

    (project_dir / "README.md").write_text(readme)

    # Create LICENSE
    license_text = dedent(f'''
        MIT License

        Copyright (c) {datetime.now().year}

        Permission is hereby granted, free of charge, to any person obtaining a copy
        of this software and associated documentation files (the "Software"), to deal
        in the Software without restriction, including without limitation the rights
        to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
        copies of the Software, and to permit persons to whom the Software is
        furnished to do so, subject to the following conditions:

        The above copyright notice and this permission notice shall be included in all
        copies or substantial portions of the Software.

        THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
        IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
        FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
        AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
        LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
        OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
        SOFTWARE.
    ''').strip()

    (project_dir / "LICENSE").write_text(license_text)

    # Create .gitignore
    gitignore = dedent('''
        # Python
        __pycache__/
        *.py[cod]
        *.so
        .Python
        build/
        dist/
        *.egg-info/

        # Virtual environments
        .venv/
        venv/

        # Testing
        .pytest_cache/
        .coverage
        htmlcov/

        # Type checking
        .mypy_cache/

        # Linting
        .ruff_cache/

        # IDEs
        .idea/
        .vscode/
        *.swp

        # OS
        .DS_Store
    ''').strip()

    (project_dir / ".gitignore").write_text(gitignore)

    # Create Makefile
    makefile = dedent(f'''
        .PHONY: help install dev test lint typecheck format clean

        help:
        \t@echo "Available commands:"
        \t@echo "  make dev        Install in development mode"
        \t@echo "  make test       Run tests"
        \t@echo "  make lint       Run linter"
        \t@echo "  make typecheck  Run type checker"
        \t@echo "  make format     Format code"
        \t@echo "  make clean      Remove build artifacts"

        dev:
        \tuv sync --extra dev

        test:
        \tuv run pytest

        lint:
        \tuv run ruff check src tests

        typecheck:
        \tuv run mypy src

        format:
        \tuv run ruff format src tests
        \tuv run ruff check --fix src tests

        clean:
        \trm -rf build dist *.egg-info
        \trm -rf .pytest_cache .mypy_cache .ruff_cache
        \trm -rf .coverage htmlcov
        \tfind . -type d -name __pycache__ -exec rm -rf {{}} +
    ''').strip()

    (project_dir / "Makefile").write_text(makefile)

    # Create GitHub Actions CI
    ci_yaml = dedent('''
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
                python-version: ["3.10", "3.11", "3.12", "3.13"]

            steps:
              - uses: actions/checkout@v4

              - name: Install uv
                uses: astral-sh/setup-uv@v5

              - name: Set up Python ${{ matrix.python-version }}
                run: uv python install ${{ matrix.python-version }}

              - name: Install dependencies
                run: uv sync --extra dev --python ${{ matrix.python-version }}

              - name: Lint
                run: uv run ruff check src tests

              - name: Type check
                run: uv run mypy src

              - name: Test
                run: uv run pytest --cov-report=xml

              - name: Upload coverage
                if: matrix.python-version == '3.12'
                uses: codecov/codecov-action@v4
    ''').strip()

    (project_dir / ".github" / "workflows" / "ci.yml").write_text(ci_yaml)

    # Create CHANGELOG
    changelog = dedent(f'''
        # Changelog

        All notable changes to this project will be documented in this file.

        ## [Unreleased]

        ### Added
        - Initial project structure

        ## [0.1.0] - {date.today().isoformat()}

        ### Added
        - Initial release
    ''').strip()

    (project_dir / "CHANGELOG.md").write_text(changelog)

    # Create .pre-commit-config.yaml
    pre_commit = dedent('''
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
    ''').strip()

    (project_dir / ".pre-commit-config.yaml").write_text(pre_commit)

    return project_dir


def main():
    parser = argparse.ArgumentParser(
        description="Create a new Python library project"
    )
    parser.add_argument("name", help="Project name (e.g., my-library)")
    parser.add_argument("--author", default="Your Name", help="Author name")
    parser.add_argument("--email", default="you@example.com", help="Author email")
    parser.add_argument("--description", default="A Python library", help="Project description")

    args = parser.parse_args()

    try:
        project_dir = create_project(
            args.name,
            author=args.author,
            email=args.email,
            description=args.description,
        )
        print(f"Created project: {project_dir}")
        print("\nNext steps:")
        print(f"  cd {args.name}")
        print("  git init")
        print("  uv sync --extra dev")
        print("  uv run pre-commit install")
        print("  uv run pytest")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
