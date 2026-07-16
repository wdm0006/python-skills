---
name: testing-python-libraries
description: Designs and implements pytest test suites for Python libraries with fixtures, parametrization, mocking, Hypothesis property-based testing, and CI configuration. Use when creating tests, improving coverage, setting up testing infrastructure, or implementing property-based testing.
---

# Python Library Testing

## Quick Start

```bash
uv run pytest                       # Run tests
uv run pytest --cov=my_library      # With coverage
uv run pytest -x                    # Stop on first failure
uv run pytest -k "test_encode"      # Run matching tests
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
- **[../project-setup/CI.md](../project-setup/CI.md)** - CI/CD test configuration

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

**Presence assertions are blind to duplicates.** `assert X in output` proves that
*at least one* X exists. It cannot tell you that there are two, or which one a
consumer will honor. That is the exact shape of bugs in generated output — HTML
tags, config keys, emitted headers — where a framework's base template and your
override each emit one and they disagree. Extract every occurrence and compare
the whole list.

```python
# BAD — passes with one correct tag, and equally with two conflicting ones.
assert '<link rel="canonical"' in html

# GOOD — pins both the count and the values.
canonicals = re.findall(r'<link rel="canonical" href="([^"]*)"', html)
assert canonicals == ["https://example.com/guide/"]
```

When two emitters produce the "same" tag they often don't format it identically
(one self-closing, one not), so anchor the pattern on the attribute you care
about and stop before the tag close — otherwise the duplicate you're hunting
slips past your regex and the test looks clean. The same rule applies to anything
countable: assert `len(rows) == 2` and the row values, not `assert rows`.

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

**Empty evaluator sets must not mean "all clear."** Auditors, policy engines,
and validation pipelines often compute a score from the enabled rules. A category
filter can accidentally disable every rule; if the scoring code maps
`results == []` to `score = 100`, an unsupported request becomes a silent perfect
pass. Treat an empty post-filter rule set as a configuration/error state, or keep
an aggregate rule enabled when it is the evaluator for every category.

```python
enabled = [rule for rule in rules if rule.supports(requested_categories)]
if not enabled:
    raise NoApplicableRulesError(requested_categories)
results = evaluate(enabled, subject)
```

Regression tests must assert more than the final score: request each supported
category (and representative combinations), assert that at least one rule ran,
and use a known failing subject so a no-op path cannot look clean.

```python
result = audit(known_noncompliant_subject, categories=["bias"])
assert result.rules_evaluated > 0
assert result.issues                 # proves filtering did not bypass evaluation
assert result.overall_score < 100
```

**Tests written around a bug.** Wrapping a call in `try/except RuinError` to make
it pass documents the bug as acceptable. Assert the *correct* behavior and let it
fail until the bug is fixed (use `xfail(strict=True)` to track it without red CI).

## Ambient State: Tests That Only Pass on Your Machine

A test that reads state it never set — environment variables, a module-level
cache, the working directory, the clock — is testing the machine as much as the
code. These are the tests that pass locally and fail in CI, or pass or fail
depending on which test ran first. Pin every input the code reads.

**Pin every variable that feeds a lookup, not just the one you know about.**
Config-directory resolution is the classic trap: setting `HOME` looks sufficient,
but on Linux the XDG variables are set independently of `HOME`, so the lookup
ignores your temp dir and every test shares one real config directory. One test's
corrupt fixture then leaks into the next, and run order decides who fails.

```python
# BAD — HOME alone. macOS ignores XDG entirely, so this passes locally forever
# and only ever fails on Linux CI.
monkeypatch.setenv("HOME", str(tmp_path))

# GOOD — pin every input to the resolution.
monkeypatch.setenv("HOME", str(tmp_path))
monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
```

When a platform difference decides whether a variable is read, the incomplete
version of the test is not "mostly right" — it is untested on exactly the
platform that runs CI.

**Import-time configuration breaks collection, not tests.** A settings object
built at module scope (`settings = Settings()`) is evaluated on import, so a
missing variable fails *collection* — before any fixture runs, so no fixture can
fix it. Declare the variables where collection can see them (pytest config, or a
root `conftest.py`), mirroring the `env:` block CI uses. Better: build config in a
factory the test can call with overrides, so importing the module is inert.

**Module-level globals outlive the test that populated them.** A cache like
`_analyzers = None` keeps one test's mocks alive for every later test. Reset it
*before and after* — the trailing reset is what stops the last test in a file from
leaking into the next file.

```python
@pytest.fixture(autouse=True)
def reset_analyzer_cache():
    app._analyzers = None
    yield
    app._analyzers = None
```

Resetting a mock has the same trap: `reset_mock()` clears recorded calls but
**keeps** `return_value` and `side_effect`, so a stub set in one test still
answers in the next.

```python
m.reset_mock()                                       # calls cleared; stub still returns 42
m.reset_mock(return_value=True, side_effect=True)    # actually resets the stub
```

**The working directory is an input.** Code that shells out inherits the process
CWD. A test asserting "runs against the path I passed" is vacuous when the test's
own CWD is already a valid project — it passes whether or not the path is
threaded through at all. Move away first, so the fallback would actually fail.

```python
def test_runs_against_given_path(tmp_path, monkeypatch, project):
    monkeypatch.chdir(tmp_path)          # empty: a CWD fallback errors here
    assert not run_tool(project_path=str(project)).startswith("Error")
```

**Freeze the clock and keep it frozen.** Restoring the real clock mid-test — to
wait on something — silently hands wall-clock time back to any date logic that
runs afterward. A business-hours branch then follows whatever the runner's local
time happens to be, so the suite is green during the day and red at night. Drive
the pending work deterministically instead of sleeping inside a frozen-clock test.

## Checklist

```
Testing:
- [ ] Tests exist for public API
- [ ] Edge cases covered (empty, boundary, error)
- [ ] No external service dependencies (mock them)
- [ ] No ambient state read unpinned (env vars, module globals, CWD, clock)
- [ ] Coverage > 85%
- [ ] Tests run in CI
```

## Learn More

This skill is based on the [Code Quality](https://mcginniscommawill.com/guides/python-library-development/#code-quality-the-foundation) section of the [Guide to Developing High-Quality Python Libraries](https://mcginniscommawill.com/guides/python-library-development/) by [Will McGinnis](https://mcginniscommawill.com/). See these posts for deeper coverage:

- [Testing with Pytest](https://mcginniscommawill.com/posts/2025-02-04-testing-pytest-intro/)
- [Testing Coverage](https://mcginniscommawill.com/posts/2025-02-09-testing-coverage/)
- [Testing with Tox](https://mcginniscommawill.com/posts/2025-02-13-testing-tox/)
- [Testing with Mocking](https://mcginniscommawill.com/posts/2025-02-16-testing-mocking/)
