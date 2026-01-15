# Makefile Reference

## Standard Makefile

```makefile
.PHONY: help install dev test lint format type-check clean build publish

help:
	@echo "Commands: dev test lint format type-check clean build publish"

dev:
	pip install -e ".[dev,docs]"
	pre-commit install

test:
	pytest

lint:
	ruff check src tests

format:
	ruff format src tests
	ruff check --fix src tests

type-check:
	mypy src

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +

build: clean
	python -m build

publish: build
	twine upload dist/*
```

## With uv (faster)

```makefile
dev:
	uv pip install -e ".[dev,docs]"
	pre-commit install

install:
	uv pip install .
```

## Additional Targets

```makefile
# Documentation
docs:
	cd docs && make html

docs-serve:
	python -m http.server --directory docs/_build/html

# Coverage report
coverage:
	pytest --cov-report=html
	open htmlcov/index.html

# Security scanning
security:
	bandit -r src/
	pip-audit
```
