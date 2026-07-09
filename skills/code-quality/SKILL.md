---
name: improving-python-code-quality
description: Improves Python library code quality through ruff linting, mypy type checking, Pythonic idioms, and refactoring. Use when reviewing code for quality issues, adding type hints, configuring static analysis tools, or refactoring Python library code.
---

# Python Code Quality

## Quick Reference

| Tool | Purpose | Command |
|------|---------|---------|
| ruff | Lint + format | `ruff check src && ruff format src` |
| mypy | Type check | `mypy src` |

## Ruff Configuration

Minimal config in pyproject.toml:

```toml
[tool.ruff]
line-length = 88
target-version = "py310"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP"]
```

For full configuration options, see **[RUFF_CONFIG.md](RUFF_CONFIG.md)**.

## MyPy Configuration

```toml
[tool.mypy]
python_version = "3.10"
disallow_untyped_defs = true
warn_return_any = true
```

For strict settings and overrides, see **[MYPY_CONFIG.md](MYPY_CONFIG.md)**.

## Type Hints Patterns

```python
# Basic
def process(items: list[str]) -> dict[str, int]: ...

# Optional
def fetch(url: str, timeout: int | None = None) -> bytes: ...

# Callable
def apply(func: Callable[[int], str], value: int) -> str: ...

# Generic
T = TypeVar("T")
def first(items: Sequence[T]) -> T | None: ...
```

For protocols and advanced patterns, see **[TYPE_PATTERNS.md](TYPE_PATTERNS.md)**.

## Common Anti-Patterns

```python
# Bad: Mutable default
def process(items: list = []):  # Bug!
    ...

# Good: None default
def process(items: list | None = None):
    items = items or []
    ...
```

```python
# Bad: Bare except
try:
    ...
except:
    pass

# Good: Specific exception
try:
    ...
except ValueError as e:
    logger.error(e)
```

```python
# Bad: truthiness guard swallows a legitimate 0 / 0.0 / "" / False
hour = config.get("start_hour") or 9   # a valid 0 (midnight) silently becomes 9
if self.max_drawdown:                  # max_drawdown=0 silently disables the limit
    enforce(self.max_drawdown)

# Good: guard on None, not on truthiness
hour = config.get("start_hour")
hour = 9 if hour is None else hour
if self.max_drawdown is not None:
    enforce(self.max_drawdown)
```

`x = x or default` is fine only when the single falsy value you mean to replace
is an empty container (e.g. `items = items or []`). For numeric, boolean, or
string fields where `0`, `False`, or `""` are meaningful inputs, it is a bug —
use `x if x is not None else default`.

```python
# Bad: identity comparison against a literal (ruff flags this as F632)
if name is not "":   # CPython interning makes it *sometimes* work — never rely on it

# Good: value comparison
if name != "":
```

## Fail Loud: Don't Degrade Silently

The costliest bugs aren't crashes — they're failures that look like success. Code
that swallows an error and returns something plausible corrupts data downstream
with no signal that anything went wrong. Prefer raising, or at minimum surfacing
an explicit error, over a quiet fallback.

**Don't collapse exceptions into a generic string — and don't discard output.**

```python
# Bad: real parse error becomes a one-line string; traceback and context lost
try:
    return parse(path)
except Exception as e:
    return {"error": str(e)}     # every distinct failure looks the same

# Bad: a nonzero exit discards stdout — where many CLIs write their real summary
result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode != 0:
    return f"Error: {result.stderr}"   # tools that exit nonzero *by design*
                                       # (e.g. "N findings") report empty here

# Good: let it raise (or return stdout+stderr+code so the caller can decide)
return {"stdout": result.stdout, "stderr": result.stderr, "code": result.returncode}
```

**Give success and failure distinct sentinels.** If the error path writes the
same status value the success path uses, failed runs read as complete.

```python
# Bad: on failure, status is set to the SAME value that means "done"
try:
    run_job()
    status = "READY"
except Exception:
    status = "READY"     # failures are now indistinguishable from success

# Good: a terminal error state the UI/caller can branch on
    status = "ERROR"
```

**Never substitute fabricated data on failure.** Returning randomized or sample
data when a fetch fails makes the UI show plausible-but-invented numbers.

```python
# Bad: a network hiccup silently becomes made-up numbers
try:
    return fetch_metrics()
except RequestError:
    return generate_sample_data()   # user can't tell real from fake

# Good: propagate the failure (or return an explicit sentinel the UI renders as an error)
```

**Signal partial results — don't return them as complete.** A paginated fetch
that aborts mid-stream and returns what it has looks identical to a full result.

```python
# Bad: caller can't distinguish "12 items" from "12 of 900 before the API died"
def fetch_all():
    items = []
    for page in paginate():
        try:
            items.extend(page)
        except RequestError:
            break            # silent truncation
    return items

# Good: return completeness alongside the data (or raise)
    return items, complete   # caller warns loudly when complete is False
```

**Batch loops: collect per-item errors, don't just `continue`.** Skipping bad
inputs silently gives no way to know coverage was incomplete — and makes sibling
operations inconsistent when some report errors and others don't.

```python
# Bad: files that fail to load vanish with no trace
for f in files:
    try:
        process(load(f))
    except Exception:
        continue                     # how many were skipped? which ones?

# Good: accumulate skips and return them so callers (and automation) can see them
errors = []
for f in files:
    try:
        process(load(f))
    except Exception as e:
        errors.append({"file": f, "error": str(e)})
return {"processed": ..., "errors": errors}
```

The unifying rule: when you catch an error, either recover meaningfully or make
the failure **visible** (raise, log at error level, or return a distinguishable
sentinel). A `return`/`continue`/fallback inside `except` that produces
normal-looking output is where silent corruption lives.

## Pythonic Idioms

```python
# Iteration
for item in items:           # Not: for i in range(len(items))
for i, item in enumerate(items):  # When index needed

# Dictionary access
value = d.get(key, default)  # Not: if key in d: value = d[key]

# Context managers
with open(path) as f:        # Not: f = open(path); try: finally: f.close()

# Comprehensions (simple only)
squares = [x**2 for x in numbers]
```

## Module Organization

```
src/my_library/
├── __init__.py      # Public API exports
├── _internal.py     # Private (underscore prefix)
├── exceptions.py    # Custom exceptions
├── types.py         # Type definitions
└── py.typed         # Type hint marker
```

## Checklist

```
Code Quality:
- [ ] ruff check passes
- [ ] mypy passes (strict mode)
- [ ] Public API has type hints
- [ ] Public API has docstrings
- [ ] No mutable default arguments
- [ ] Specific exception handling
- [ ] Failures fail loud — no fabricated fallbacks, colliding success/error sentinels, or silently-truncated results
- [ ] Batch loops collect per-item errors instead of a bare `continue`
- [ ] Truthiness guards don't swallow valid 0/False/"" (guard on `is None`)
- [ ] No `is`/`is not` against literals (use ==/!=)
- [ ] py.typed marker present
```

## Learn More

This skill is based on the [Code Quality](https://mcginniscommawill.com/guides/python-library-development/#code-quality-the-foundation) section of the [Guide to Developing High-Quality Python Libraries](https://mcginniscommawill.com/guides/python-library-development/) by [Will McGinnis](https://mcginniscommawill.com/). See these posts for deeper coverage:

- [Linting & Formatting with Ruff](https://mcginniscommawill.com/posts/2025-01-30-linting-formatting-ruff/)
- [Understanding McCabe Complexity](https://mcginniscommawill.com/posts/2025-04-24-understanding-mccabe-complexity/)
- [Adding Type Hints](https://mcginniscommawill.com/posts/2025-04-03-pygeohash-type-hints/)
