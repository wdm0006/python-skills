#!/usr/bin/env python3
"""Create a new Python library project with modern best practices.

Usage:
    python create_project.py my-library
    python create_project.py my-library --author "Your Name" --email you@example.com
"""

import argparse
import os
from pathlib import Path
from textwrap import dedent


def create_project(
    name: str,
    author: str = "Your Name",
    email: str = "you@example.com",
    description: str = "A Python library",
) -> Path:
    """Create a new Python library project structure."""
    # Convert name to valid Python package name
    package_name = name.replace("-", "_").lower()
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
        name = "{name}"
        version = "0.1.0"
        description = "{description}"
        readme = "README.md"
        requires-python = ">=3.10"
        license = {{text = "MIT"}}
        authors = [
            {{name = "{author}", email = "{email}"}}
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

        [project.urls]
        Homepage = "https://github.com/username/{name}"
        Repository = "https://github.com/username/{name}"

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
        """{description}."""

        __version__ = "0.1.0"
    ''').strip()

    (project_dir / "src" / package_name / "__init__.py").write_text(init_py)

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
    (project_dir / "tests" / f"test_{package_name}.py").write_text(test_init)

    # Create README
    readme = dedent(f'''
        # {name}

        {description}

        ## Installation

        ```bash
        pip install {name}
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
        pip install -e ".[dev]"

        # Run tests
        pytest

        # Run linting
        ruff check src tests
        ```

        ## License

        MIT License
    ''').strip()

    (project_dir / "README.md").write_text(readme)

    # Create LICENSE
    license_text = dedent('''
        MIT License

        Copyright (c) 2024

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
        .PHONY: help install dev test lint format clean

        help:
        \t@echo "Available commands:"
        \t@echo "  make dev      Install in development mode"
        \t@echo "  make test     Run tests"
        \t@echo "  make lint     Run linter"
        \t@echo "  make format   Format code"
        \t@echo "  make clean    Remove build artifacts"

        dev:
        \tpip install -e ".[dev]"

        test:
        \tpytest

        lint:
        \truff check src tests

        format:
        \truff format src tests
        \truff check --fix src tests

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
                python-version: ["3.10", "3.11", "3.12"]

            steps:
              - uses: actions/checkout@v4

              - name: Set up Python ${{ matrix.python-version }}
                uses: actions/setup-python@v5
                with:
                  python-version: ${{ matrix.python-version }}

              - name: Install dependencies
                run: pip install -e ".[dev]"

              - name: Lint
                run: ruff check src tests

              - name: Type check
                run: mypy src

              - name: Test
                run: pytest --cov-report=xml

              - name: Upload coverage
                if: matrix.python-version == '3.11'
                uses: codecov/codecov-action@v3
    ''').strip()

    (project_dir / ".github" / "workflows" / "ci.yml").write_text(ci_yaml)

    # Create CHANGELOG
    changelog = dedent('''
        # Changelog

        All notable changes to this project will be documented in this file.

        ## [Unreleased]

        ### Added
        - Initial project structure

        ## [0.1.0] - YYYY-MM-DD

        ### Added
        - Initial release
    ''').strip()

    (project_dir / "CHANGELOG.md").write_text(changelog)

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
        print(f"\nNext steps:")
        print(f"  cd {args.name}")
        print(f"  git init")
        print(f"  pip install -e '.[dev]'")
        print(f"  pytest")
    except ValueError as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
