---
name: designing-python-apis
description: Designs intuitive Python library APIs following principles of simplicity, consistency, and discoverability. Handles API evolution, deprecation, breaking changes, and error handling. Use when designing new library APIs, reviewing existing APIs for improvements, or managing API versioning and deprecations.
---

# Python API Design

## Core Principles

1. **Simplicity**: Simple things simple, complex things possible
2. **Consistency**: Similar operations work similarly
3. **Least Surprise**: Behave as users expect
4. **Discoverability**: Find via autocomplete and help

## Progressive Disclosure Pattern

```python
# Level 1: Simple functions
from mylib import encode, decode
result = encode(37.7749, -122.4194)

# Level 2: Configurable classes
from mylib import Encoder
encoder = Encoder(precision=15)

# Level 3: Low-level access
from mylib.internals import BitEncoder
```

## Naming Conventions

```python
# Actions: verbs
encode(), decode(), validate()

# Retrieval: get_*
get_user(), get_config()

# Boolean: is_*, has_*, can_*
is_valid(), has_permission()

# Conversion: to_*, from_*
to_dict(), from_json()
```

## Error Handling

```python
class MyLibError(Exception):
    """Base exception with helpful messages."""
    def __init__(self, message: str, *, hint: str = None):
        super().__init__(message)
        self.hint = hint

# Usage
raise ValidationError(
    f"Latitude must be -90 to 90, got {lat}",
    hint="Did you swap latitude and longitude?"
)
```

### Fail Loud, Not Silent

The most expensive bugs are the ones where **failure is indistinguishable from
success**. A caller who gets no error assumes everything worked. These patterns
all turned a real failure into a silent wrong answer in shipped code — guard
against every one.

**Don't write the success sentinel on the failure path.** An `except` block that
sets the same state a successful run would makes failed jobs look complete.

```python
# BAD — any failure is reported to the user as a finished result.
try:
    result = run_job()
    status = "READY"
except Exception:
    status = "READY"        # failure now looks identical to success

# GOOD — distinct terminal states; the UI/caller can react.
try:
    result = run_job()
    status = "READY"
except Exception:
    log.exception("job failed")
    status = "ERROR"
```

**Don't swallow distinct failures into one generic message.** A broad
`except Exception` that returns `"error: something went wrong"` (or worse, an
empty result) collapses parse errors, missing files, and bugs into the same
opaque string — undebuggable and often mistaken for "no problems found." Catch
the specific exceptions you can handle; let the rest propagate.

**An empty/partial result is not an error signal.** Returning `[]`, an empty
`DataFrame`, or "what I fetched before the connection dropped" looks like a valid
answer. Pagination that returns partial pages on a mid-stream `RequestError`, then
gets aggregated as if complete, produces silently wrong analytics. Either raise,
or return an explicit "incomplete" marker the caller must check — never let
truncation masquerade as the full set.

**A no-op on unexpected input is a silent corruption.** Code that skips columns
of the wrong type, ignores a key it doesn't recognize, or `continue`s past a file
it can't parse — with no error and no report — leaves the caller believing the
operation applied. If you can't act on an input, say so (raise, warn, or return a
per-item error list); don't quietly do nothing.

**Validation errors must not leave partial mutations behind.** An `inplace=True`
API that renames caller-owned columns and only then validates another argument can
raise the right exception while still corrupting the caller's next operation.
Validate every parameter and precondition before the first mutation. When work
cannot be validated up front, stage it on a copy and commit only after success.

```python
# BAD — invalid max_fraction still changes the caller's dataframe.
def detect(data, *, max_fraction=0.1, inplace=True):
    target = data if inplace else data.copy()
    target.rename(columns={"time": "timestamp"}, inplace=True)
    if not 0 < max_fraction < 0.5:
        raise ValueError("max_fraction must be between 0 and 0.5")
    return analyze(target)

# GOOD — the error path is side-effect free.
def detect(data, *, max_fraction=0.1, inplace=True):
    if not 0 < max_fraction < 0.5:
        raise ValueError("max_fraction must be between 0 and 0.5")
    target = data if inplace else data.copy()
    target.rename(columns={"time": "timestamp"}, inplace=True)
    return analyze(target)
```

Pin the contract in tests: snapshot caller-owned state, trigger a late validation
error with `inplace=True`, and assert the object is unchanged. Testing only the
exception type misses the damaging half of this bug.

```python
before = frame.copy(deep=True)
with pytest.raises(ValueError, match="max_fraction"):
    detect(frame, max_fraction=0.5, inplace=True)
pd.testing.assert_frame_equal(frame, before)
```

**Filtering down to empty must never read as "all clear."** When you narrow a rule
set, check set, or work list and the filter yields nothing, an "evaluate all →
0 problems" path reports a perfect score while actually checking nothing. Guard
the empty case explicitly:

```python
selected = [r for r in rules if r.category in requested]
if not selected:                       # empty filter ≠ everything passed
    raise ValueError(f"no rules match {requested!r}")
```

**Never fabricate a fallback that looks real.** Substituting sample/random data
when a fetch fails (so the UI "has something to show") presents invented numbers
as genuine. Surface the failure instead; a visible error beats a plausible lie.

**Don't discard the real output on a non-zero exit.** A subprocess wrapper that
returns `f"Error: {stderr}"` whenever `returncode != 0` loses the answer for tools
that exit non-zero by design and write results to **stdout** — reporting a
successful run as an empty `"Error: "`. Inspect stdout and the actual exit
semantics before deciding it failed.

## Deprecation

Deprecate gracefully: warn now, document the removal version, and remove only in a
major release. The warning mechanics (including deprecating parameters, classes,
and modules) and the migration-guide template are owned by the
`managing-python-releases` skill — see
**[../release-management/MIGRATION.md](../release-management/MIGRATION.md)**.

## Anti-Patterns

```python
# Bad: Boolean trap
process(data, True, False, True)

# Good: Keyword arguments
process(data, validate=True, cache=False)
```

The mutable-default-argument trap (`def f(x: list = [])`) is covered by the
`improving-python-code-quality` skill.

For detailed patterns, see:
- **[PATTERNS.md](PATTERNS.md)** - Builder, factory, and advanced patterns
- **[EVOLUTION.md](EVOLUTION.md)** - API versioning and migration guides

## Review Checklist

```
Naming:
- [ ] Clear, self-documenting names
- [ ] Consistent patterns throughout
- [ ] Boolean params read naturally

Parameters:
- [ ] Minimal required parameters
- [ ] Sensible defaults
- [ ] Keyword-only after positional clarity

Errors:
- [ ] Custom exceptions with context
- [ ] Helpful error messages
- [ ] Documented in docstrings
- [ ] Failures fail loud — no success sentinel on the error path
- [ ] Empty/partial results never masquerade as a complete answer
- [ ] No silent no-ops or fabricated fallback data
- [ ] Validation failures leave caller-owned inputs unchanged
```

## Learn More

This skill is based on the [Ergonomics](https://mcginniscommawill.com/guides/python-library-development/#ergonomics-the-joy-of-good-design) section of the [Guide to Developing High-Quality Python Libraries](https://mcginniscommawill.com/guides/python-library-development/) by [Will McGinnis](https://mcginniscommawill.com/). See these posts for deeper coverage:

- [The Art of API Design](https://mcginniscommawill.com/posts/2025-02-03-art-of-api-design/)
- [Designing for Developer Joy](https://mcginniscommawill.com/posts/2025-02-06-designing-for-developer-joy/)
