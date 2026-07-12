# Deprecation & Migration

The mechanics of deprecating and removing API surface, and the template for the
migration guide that ships with a major release. This is the canonical home for
the deprecation-warning pattern; the api-design skill covers *whether* a change
should be additive or breaking.

## Contents
- Deprecation lifecycle
- Emitting deprecation warnings
- Deprecating parameters and classes
- Choosing the warning category
- Migration guide template

## Deprecation lifecycle

A public name is removed over at least one minor cycle, never in a patch:

1. **Deprecate** in a minor release — still works, warns, documented under
   `### Deprecated` in the changelog with the target removal version.
2. **Keep** through subsequent minors so downstream code has time to migrate.
3. **Remove** only in the next major release.

## Emitting deprecation warnings

`stacklevel=2` points the warning at the *caller's* line, not this function.

```python
import warnings


def old_function(*args, **kwargs):
    """Deprecated since 1.4; use new_function(). Removed in 2.0."""
    warnings.warn(
        "old_function() is deprecated and will be removed in 2.0.0; "
        "use new_function() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return new_function(*args, **kwargs)
```

## Deprecating parameters and classes

Deprecate one argument while keeping the rest working with a sentinel default:

```python
_UNSET = object()

def connect(host, *, timeout=_UNSET, timeout_s=30):
    if timeout is not _UNSET:
        warnings.warn(
            "`timeout` is deprecated; use `timeout_s`.",
            DeprecationWarning, stacklevel=2,
        )
        timeout_s = timeout
    ...
```

For a class, warn in `__init__`. For a whole module, warn at import time via
`__getattr__` (PEP 562) so only accessing the deprecated name triggers it.

## Choosing the warning category

- `DeprecationWarning` — the default. Hidden from end users, shown to test suites
  and to developers running with `-W`. Correct for library-internal deprecations.
- `FutureWarning` — shown to end users by default. Use when the *behavior* of an
  unchanged call will change (e.g. a default flips) and everyone needs to notice.

Test that the warning fires:

```python
import pytest

def test_old_function_warns():
    with pytest.warns(DeprecationWarning, match="removed in 2.0.0"):
        old_function()
```

## Migration guide template

Ship `docs/migration/vX.md` with every major release:

```markdown
# Migrating to X.0

## Summary
One paragraph: who is affected and the headline changes.

## Breaking changes
### <name> removed
- **Was:** `old_function(a, b)`
- **Now:** `new_function(a, b)`
- **Why:** <reason>
- **Automated fix:** `sed -i 's/old_function/new_function/g' ...` (if mechanical)

## Deprecations (still work, will be removed)
- `<name>` — replace with `<replacement>` before Y.0

## New defaults
- `<setting>` now defaults to `<value>` (was `<old>`); pass it explicitly to keep the old behavior.
```
