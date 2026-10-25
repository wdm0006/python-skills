#!/usr/bin/env bash
# Scaffold a library and run its own gates, then import the built wheel from
# outside the project. Not part of the stdlib unittest suite (needs network).
set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

cd "$work"
uv run --no-project --python 3.12 python \
  "$repo/skills/python/project-setup/scripts/create_project.py" smoke-lib

cd smoke-lib
uv sync --python 3.12 --extra dev
uv run ruff check src tests
uv run ruff format --check src tests
uv run pytest
uv run mypy src
uv build

venv="$work/wheel-venv"
uv venv --python 3.12 "$venv"
uv pip install --python "$venv/bin/python" dist/*.whl

cd "$work"
"$venv/bin/python" -c "
import smoke_lib
assert '$work/smoke-lib/src' not in smoke_lib.__file__, smoke_lib.__file__
assert '$venv' in smoke_lib.__file__, smoke_lib.__file__
print('wheel import ok:', smoke_lib.__file__)
"
