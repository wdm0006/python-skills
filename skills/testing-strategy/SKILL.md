---
name: testing-python-libraries
description: Designs and implements pytest test suites for Python libraries with fixtures, parametrization, mocking, Hypothesis property-based testing, and CI configuration. Use when creating tests, improving coverage, setting up testing infrastructure, or implementing property-based testing.
---

# Python Library Testing

## Quick Start

```bash
pytest                              # Run tests
pytest --cov=my_library             # With coverage
pytest -x                           # Stop on first failure
pytest -k "test_encode"             # Run matching tests
```

## Pytest Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra -q --cov=my_library --cov-fail-under=85"

[tool.coverage.run]
branch = true
source = ["src/my_library"]
```

## Test Structure

```
tests/
├── conftest.py           # Shared fixtures
├── test_encoding.py
└── test_decoding.py
```

## Essential Patterns

**Basic test:**
```python
def test_encode_valid_input():
    result = encode(37.7749, -122.4194)
    assert isinstance(result, str)
    assert len(result) == 12
```

**Parametrization:**
```python
@pytest.mark.parametrize("lat,lon,expected", [
    (37.7749, -122.4194, "9q8yy"),
    (40.7128, -74.0060, "dr5ru"),
])
def test_known_values(lat, lon, expected):
    assert encode(lat, lon, precision=5) == expected
```

**Fixtures:**
```python
@pytest.fixture
def sample_data():
    return [(37.7749, -122.4194), (40.7128, -74.0060)]

def test_batch(sample_data):
    results = batch_encode(sample_data)
    assert len(results) == 2
```

**Mocking:**
```python
def test_api_call(mocker):
    mocker.patch("my_lib.client.fetch", return_value={"data": []})
    result = my_lib.get_data()
    assert result == []
```

**Exception testing:**
```python
def test_invalid_raises():
    with pytest.raises(ValueError, match="latitude"):
        encode(91.0, 0.0)
```

For detailed patterns, see:
- **[FIXTURES.md](FIXTURES.md)** - Advanced fixture patterns
- **[HYPOTHESIS.md](HYPOTHESIS.md)** - Property-based testing
- **[CI.md](CI.md)** - CI/CD test configuration

## Test Principles

| Principle | Meaning |
|-----------|---------|
| Independent | No shared state between tests |
| Deterministic | Same result every run |
| Fast | Unit tests < 100ms each |
| Focused | Test behavior, not implementation |

## Tests That Lie: Avoiding False-Green

A passing suite is worthless if it can't fail when the code is wrong. The most
expensive bugs ship under green CI. Audit for these anti-patterns — each is a way
"all tests pass" can mask broken behavior.

**Conditional assertions that vacuously pass.** If the setup silently fails, a
guarded assertion never runs and the test still passes.

```python
# BAD — if the Sphinx build fails, no index.html, so nothing is asserted.
def test_build_includes_css():
    if index_html.exists():            # build broke? test passes anyway.
        assert "theme.css" in index_html.read_text()

# GOOD — assert the precondition, then the behavior.
def test_build_includes_css():
    assert index_html.exists(), "build produced no index.html"
    assert "theme.css" in index_html.read_text()
```

**Over-permissive assertions.** An `or` that can't fail, or a substring match so
loose it accepts wrong output.

```python
assert result.returncode == 0 or "html_static_path" in result.stderr  # masks real failures
assert "ui" in todo.tags                                              # also matches "build"
```

**Mocking the thing under test.** If you patch `_run_command` and only assert the
argv tokens, the test locks in a command that may not exist — it stays green even
after the subcommands or flags it builds are renamed or removed upstream. Mock at
the boundary (the subprocess/HTTP call), then assert on the **parsed result**, not
on the arguments you passed in.

**Fakes that ignore the parameters being tested.** A fake client whose
`list_items` returns all canned rows in one call — ignoring `after` and
pagination — cannot exercise the pagination or incremental-sync logic those
parameters drive, so it stays unverified. Make fakes honor the parameters whose
handling is the point of the test.

**Smoke tests that import the wrong thing.** `python -c "import server"` can print
success by resolving an empty `server/` package that shadows the real `server.py`
— a broken wheel that still "imports." Assert a real symbol is reachable
(`from server import main; main`), not merely that an import name resolves.

**Forgotten mock → silent real network calls.** A test missing its `httpx_mock`
fixture hits the live API: slow, flaky, rate-limited, and silently exercising
nothing deterministic. Add `--disable-socket` (pytest-socket) so any unmocked
network call fails loudly instead of "passing."

**No-op CI gates.** Confirm the gate actually runs the tests:
- `go test ./...` / `pytest` with **zero test files** is a green no-op.
- Files excluded via `--ignore` or `pytest.mark.skip` "because flaky" often fail
  *deterministically* — exclusion hides real breakage, not flakiness.
- Marker filters (`-m "not integration"`) can deselect the only meaningful tests.
  Reproduce CI's exact marker expression locally before trusting green.

**Tests written around a bug.** Wrapping a call in `try/except RuinError` to make
it pass documents the bug as acceptable. Assert the *correct* behavior and let it
fail until the bug is fixed (use `xfail(strict=True)` to track it without red CI).

## Catch Deprecation Drift Before It Breaks You

A dependency deprecates an API in one release and removes it in the next. Code
that calls the deprecated form keeps working — emitting a `DeprecationWarning` or
`FutureWarning` nobody reads — right up until a routine `pip install -U` upgrades
past the removal and the call becomes a hard `AttributeError`/`TypeError`. By
then the break is a production incident, not a warning.

This is the same failure mode across every ecosystem: `DataFrame.append` (removed
in pandas 2.0), `matplotlib.cm.get_cmap` (removed in 3.9), a networkx layout
helper renamed out of the top-level namespace, `datetime.utcnow()` (deprecated in
3.12, hundreds of warnings buried in the log). In each case the signal existed as
a warning for a full release cycle and was ignored.

Turn that warning into a test failure so it fails loud while it's still just a
deprecation:

```toml
[tool.pytest.ini_options]
filterwarnings = [
    "error",                                    # any warning fails the test
    # Targeted, documented escape hatches for warnings you can't fix yet:
    "ignore:.*legacy config.*:DeprecationWarning:some_dependency",
]
```

`"error"` promotes every warning to an exception, so a `DeprecationWarning` from a
dependency (or from your own soon-to-break call) turns a green suite red the day
the warning first appears — months before the removal lands. Add a *narrow,
commented* `ignore` entry (scoped by message and module) for third-party warnings
you genuinely can't act on yet; never blanket-ignore a whole category, or you
re-bury the signal you just surfaced.

Two habits make this land:

- **Don't pin ancient dependencies and forget them.** A lockfile frozen on a
  years-old release hides every deprecation the ecosystem has issued since. Test
  against a current resolution (e.g. a periodic unpinned CI job) so drift shows up
  as a failing warning, not a surprise years later.
- **When you wrap an external CLI or library, verify its *installed* API, not the
  one you remember.** Code written against a tool's 2.x commands while the project
  pins 3.x fails only at runtime — and unit tests that mock the subprocess pass
  green while asserting flags that no longer exist. Check the real version's
  surface (`--help`, `inspect`, the changelog) before asserting against it.

## Checklist

```
Testing:
- [ ] Tests exist for public API
- [ ] Edge cases covered (empty, boundary, error)
- [ ] No external service dependencies (mock them)
- [ ] Coverage > 85%
- [ ] Tests run in CI
- [ ] filterwarnings = ["error"] so deprecations fail loud (with narrow, commented ignores only)
```

## Learn More

This skill is based on the [Code Quality](https://mcginniscommawill.com/guides/python-library-development/#code-quality-the-foundation) section of the [Guide to Developing High-Quality Python Libraries](https://mcginniscommawill.com/guides/python-library-development/) by [Will McGinnis](https://mcginniscommawill.com/). See these posts for deeper coverage:

- [Testing with Pytest](https://mcginniscommawill.com/posts/2025-02-04-testing-pytest-intro/)
- [Testing Coverage](https://mcginniscommawill.com/posts/2025-02-09-testing-coverage/)
- [Testing with Tox](https://mcginniscommawill.com/posts/2025-02-13-testing-tox/)
- [Testing with Mocking](https://mcginniscommawill.com/posts/2025-02-16-testing-mocking/)
