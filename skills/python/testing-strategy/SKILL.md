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

## Prove the Test Can Fail: Mutate the Fix

Every regression test makes an implicit claim — *this would have caught the bug*.
The only way to check the claim is to put the bug back and watch the test go red.
Do it once, while the fix is still fresh in your head; it takes a minute and it is
the difference between a regression test and a decoration.

```bash
# 1. revert the fix (git stash, or hand-edit the guard back to its broken form)
# 2. run ONLY the new test — it must FAIL, and for the right reason
uv run pytest tests/test_paths.py::test_symlink_escape_rejected -q
# 3. restore the fix — it must pass
```

**Mutate each half of a compound guard separately.** A fix that validates an input
*and* re-checks the resolved result looks redundant until you revert each half on
its own.

```python
def _resolve_baseline(name: str) -> Path:
    if ".." in name or not NAME_RE.fullmatch(name):   # mutation A
        raise ValueError(name)
    path = (BASE_DIR / f"{name}.json").resolve()
    if not path.is_relative_to(BASE_DIR.resolve()):   # mutation B
        raise ValueError(name)
    return path
```

Reverting A is caught by a `../../etc/passwd` test. Reverting B is caught *only*
by a symlink placed inside the approved directory that points outside it — a test
most suites don't have. If reverting one half leaves the suite green, you have a
test gap, not a redundant check: write the test that pins it.

**Know what "red" looks like for the mutation you chose.** A reintroduced bug does
not always surface as a clean assertion failure.

- Remove a retry/iteration cap and the suite **hangs** instead of failing. Run the
  mutated suite under an external timeout — `timeout 60 uv run pytest -q` with no
  output *is* the reproduction. Making the cap merely unreachable (`> 10**9`) is
  the honest mutation; the off-by-one (`>` → `>=`) fails loudly and is the cheaper
  one to re-run day to day.
- Drop an `await` or a `try` in async code and the runner may die with an unhandled
  rejection and a worker crash rather than a named test failure. Still red — read
  the output before concluding your test didn't fire.
- If the mutated run errors during *collection*, no test ran at all and you have
  learned nothing about the test.

**A hand-written fixture is itself a mutation — of reality.** When the same person
authors both a parser and every fixture it is tested against, both encode the same
assumption, and the suite is green against a guard that cannot fire in production.
A regex requiring single spaces between tokens matches hand-typed single-space
fixtures forever, while the live document renders those tokens across indented
lines. Capture at least one fixture from the real source, commit it, and point the
guard's test at that.

## Mutate in Both Directions: A Guard Can Also Fire Too Often

A fix that adds a conditional — a warning on incomplete data, a validation check,
a flag that suppresses a claim — has *two* plausible wrong implementations, not
one: it never fires (the original bug), or it always fires (over-broad). The
regression test you naturally write covers only the first. Mutate both ways.

```python
# The fix: warn when a sub-fetch failed, so a partial total isn't read as complete.
if failed_sources:
    log.warning("counts UNDERCOUNT: no data from %s", ", ".join(failed_sources))

# Mutation 1 — the original bug. Delete the tracking so the list is always empty.
# Mutation 2 — over-broad. Drop the condition, or write `if not sources:`.
```

**The control test is the one that catches mutation 2, and it looks vacuous.** A
test asserting that a fully successful run emits *no* warning passes on the
pre-fix code by construction, so it reads like it proves nothing and gets cut in
review. It is the only test that fails when the warning becomes unconditional.
Keep it, and name the pairing explicitly in the PR body so a reviewer doesn't
delete half the coverage:

| mutation                              | test that goes red                 |
| ------------------------------------- | ---------------------------------- |
| tracking removed (never warns)        | `test_failed_source_warns`         |
| condition removed (always warns)      | `test_healthy_run_emits_no_warning`|

**Truthiness is how guards become over-broad.** The over-firing mutation is rarely
a deliberate edit — it is `if not x:` where the intent was "this value is absent".
`None` means *unmeasurable / the fetch failed*; `[]`, `0`, `0.0` and `""` are
legitimate healthy results that a truthiness check silently folds in with it.

```python
# BAD — fires on a resource that genuinely has no referrers, or a real count of 0.
if not referrers:
    warn_incomplete(name)

# GOOD — only the sentinel means "we don't know".
if referrers is None:
    warn_incomplete(name)
```

A useful tell that you got this wrong: existing fixtures that pass empty
collections start emitting the new warning. If adding a guard turns unrelated
tests red, read those failures as the over-broad mutation reporting itself rather
than as fixtures needing an update.

**Attribute each mutation to exactly one test.** When a fix has several parts,
revert them one at a time and record which test fails for each. "Deleting only
the `bool` short-circuit fails exactly one test" is a checked statement; "the
suite covers this" is not. A part whose removal leaves the suite green is a gap.

## Pick Fixture Values That Separate the Bug From the Fix

A test survives mutation most often because its *data* cannot tell the two
implementations apart. Before writing the assertion, work out what the buggy
version would produce from your fixture. If it produces the same number, the
fixture is the problem — change it, not the assertion.

**Order-sensitive readings need a fixture whose ends differ.** A summary that
prints the latest value from an already-sorted frame reads `.iloc[0]` when the
sort is descending and `.iloc[-1]` when it is ascending; both are one character
apart and only one is right. A single-row or flat fixture makes them agree.

```python
# BAD — every row carries the same total, so first and last agree and the
# assertion holds against either reading.
rows = [{"day": "2024-01-01", "cumulative": 5}]

# GOOD — strictly increasing across three days: 2, then 5, then 9. Only the
# correct reading yields 9.
rows = [
    {"day": "2024-01-01", "cumulative": 2},
    {"day": "2024-01-02", "cumulative": 5},
    {"day": "2024-01-03", "cumulative": 9},
]
assert "Final cumulative stars: 9" in captured.messages
```

**For per-group derived columns, the two readings must disagree on every row.**
A gap/delta/rank column computed per group and the same column computed over the
globally sorted table often coincide for most rows; interleaving two groups is not
enough on its own — the values have to come out different. Two items per group,
timed so the within-group spacing and the global spacing diverge, is the smallest
fixture that pins it:

| group | dates                    | per-group gaps | global-sort gaps |
| ----- | ------------------------ | -------------- | ---------------- |
| A     | 2024-01-01, 2024-01-11   | 10.0           | 5.0, 5.0, 10.0   |
| B     | 2024-01-06, 2024-01-21   | 15.0           | (one blank)      |

Per group there are two blanks and gaps of 10.0 and 15.0; globally there is one
blank and no value matches. Assert the exact numbers *and* the blank count.

**A fixture that reproduces the bug's magic constant proves nothing.** When the
defect is a redundant fixed wait of 60 seconds and the legitimate code path also
falls back to 60 seconds when a header is missing, a fixture that omits the header
passes on both. Supply a value that makes the legitimate result distinct — a reset
header five seconds out — so the extra wait is visible.

**Record the sequence, not the fact.** A no-op stub answers "did it sleep?" and
nothing else. Collect the arguments instead and assert the whole call sequence;
that is what catches one extra call in the middle.

```python
# BAD — passes whether the code sleeps once or twice.
monkeypatch.setattr("mypkg.client.time.sleep", lambda _s: None)

# GOOD — the sequence is the assertion.
sleeps: list[float] = []
monkeypatch.setattr("mypkg.client.time.sleep", sleeps.append)
...
assert sleeps == [reset_wait, 0.1]   # reset wait, then the post-success pause
```

## Changing Behavior an Existing Test Already Asserts

Before you change any output, read what the suite already claims about it. Three
situations look identical from a green run:

1. **Shape assertions only** — `isinstance(x, float)`, `>= 0`, `"minutes" in
   result`. The behavior is *unspecified*: the test passed before your fix and
   will pass after it, and would have passed on almost any output. Treat this as
   no coverage, not as coverage you must preserve.
2. **The correct value is pinned.** Your "fix" is the regression. Stop.
3. **The buggy value is pinned.** A confident exact-match assertion on wrong
   output makes the defect read as tested-and-intended.

Green is not evidence of intent, and the test cannot tell you which of 2 and 3 you
are in — only the docs, the docstring, or the issue history can. Both shapes occur
in the same file: a renderer that deliberately drops list markers has a test
pinning the marker-free output, and the accidental defect two functions over where
heading text fuses onto the next block has an equally confident pinned test. If
the intent is written down nowhere, writing it down is part of the fix.

**Grep for every assertion that pins the old value — not just the one the issue
named.** A ticket cites the obvious single-case test; the same wrong output is
usually also embedded inside a multi-line `expected` string in some
`test_mixed_content`-style case, where it does not look like the thing you are
changing.

```bash
# search for a distinctive slice of the OLD output, not for the test's name
rg -l 'HeadingBody text' tests/
```

**Prefer a differential assertion over a magic constant.** When the number comes
from a third-party computation you do not control — a readability scorer, a
tokenizer, a formatter — an exact float pins your test to that library's version.
If the dependency is declared unpinned (`"textstat"`, no specifier), a patch
release moves the value and the test goes red with no change in your code. Assert
the *relationship the fix establishes* instead:

```python
# BAD — version-brittle, and it only says "some number came out".
assert readability(MARKDOWN)["flesch"] == 42.80

# GOOD — the property the fix creates: markup must not affect the score.
assert readability(MARKDOWN)["flesch"] == readability(PLAIN_EQUIVALENT)["flesch"]
assert strip_markup(MARKDOWN) == PLAIN_EQUIVALENT      # exact, no library constant
assert len(strip_markup(MARKDOWN).split()) == 27
```

The differential form needs no constant from the dependency at all, and it still
goes red the moment the stripper regresses.

**If you do pin a number, measure it — never estimate.** Derived metrics are not
intuitive, and a tolerance tight enough to be meaningful is tight enough that a
plausible guess fails on the first CI run. Compute it, then paste the result:

```bash
uv run python -c "from mypkg import readability; \
  print(readability(open('tests/data/doc.md').read()))"
```

Size the tolerance against the bug's own gap rather than your confidence: if the
buggy and fixed paths differ by ~29 points, `pytest.approx(42.80, abs=1.0)` is
both a real value assertion and tolerant of a dependency bump.

**To quote the "before" number in the test's comment, load the old module
directly** — you do not need to check out the old tree:

```bash
git show main:mypkg/parser.py > /tmp/old_parser.py
```

```python
spec = importlib.util.spec_from_file_location("old_parser", "/tmp/old_parser.py")
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
print(readability(old.strip_markup(MARKDOWN)))   # what the buggy path used to yield
```
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
- [ ] Each regression test verified red against the reverted fix
- [ ] New guards mutated both ways (never fires / always fires), each mutation
      attributed to one test; control test for the healthy case kept
- [ ] Absence checked with `is None`, not truthiness (`[]`/`0`/`""` are real values)
- [ ] Fixture values make the buggy and correct readings produce different results
- [ ] Existing assertions on changed output classified (shape-only / pins correct
      value / pins the bug), and every file embedding the old value updated
- [ ] Values from third-party computations asserted differentially, or measured
      and pinned with a tolerance sized to the bug's gap — never estimated
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
