# MyPy Configuration Reference

## Strict Configuration

```toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false

[[tool.mypy.overrides]]
module = "third_party.*"
ignore_missing_imports = true
```

## Gradual Adoption

Start lenient, tighten over time:

```toml
# Phase 1: Basic
[tool.mypy]
python_version = "3.10"
warn_return_any = true

# Phase 2: Require types on new code
disallow_untyped_defs = true
disallow_incomplete_defs = true

# Phase 3: Full strict
strict = true
```

## Common Fixes

```python
# Error: Missing return type
def process(x):  # Add: -> ReturnType
    ...

# Error: Incompatible types
x: str = 123  # Fix: x: int = 123

# Error: Missing type for argument
def func(data):  # Add: data: dict[str, Any]
    ...

# Silence specific line
x = untyped_call()  # type: ignore[no-untyped-call]
```

## Type Stubs

For libraries without type hints:

```bash
# Install stubs
pip install types-requests types-PyYAML

# Or ignore in config
[[tool.mypy.overrides]]
module = "untyped_library.*"
ignore_missing_imports = true
```
