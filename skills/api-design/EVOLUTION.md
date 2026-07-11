# API Evolution

Changing a published API without breaking the people who depend on it. This file
covers the *design* decisions of evolution. For the mechanics of emitting
deprecation warnings and coordinating them with version bumps, changelogs, and
release timing, see the `managing-python-releases` skill.

## Contents

- [Additive vs Breaking Change](#additive-vs-breaking-change)
- [What "Public" Means](#what-public-means)
- [The Deprecation Lifecycle](#the-deprecation-lifecycle)
- [Backward-Compatible Signature Changes](#backward-compatible-signature-changes)
- [Feature-Flagging New Behavior](#feature-flagging-new-behavior)

## Additive vs Breaking Change

The dividing question: can code written against the old API still run unchanged?

**Additive (safe, minor release):**

- Adding a new function, class, or method.
- Adding a keyword-only parameter *with a default*.
- Widening what an argument accepts (accepting `str | Path` where it took `str`).
- Adding a field to a returned dataclass or `NamedTuple` (see the structured
  return types pattern in PATTERNS.md) — but note callers who unpack a
  fixed-length tuple can still break, so append fields, never reorder.

**Breaking (major release only):**

- Removing or renaming anything public.
- Removing a parameter, or making an optional one required.
- Changing a return type, a default value, or observable behavior.
- Tightening what an argument accepts.
- Reordering positional parameters.

When in doubt, assume some user relies on the current behavior — including
behavior you consider a bug. "Nobody could depend on that" is usually wrong.

## What "Public" Means

You are only obligated to preserve what you promised. Make the boundary explicit
so you can refactor internals freely.

- **`__all__`** declares a module's public names. It controls `from mod import *`
  and signals intent to readers and tools. Everything not in `__all__` is fair
  game to change.

```python
__all__ = ["encode", "decode", "Encoder"]

def encode(...): ...
def _normalize(...): ...   # private: refactor or delete anytime
```

- **Leading underscore** marks a name private regardless of `__all__`. A module,
  function, attribute, or class starting with `_` carries no compatibility
  guarantee.
- **Document the contract.** If it's in the public docs and reachable without an
  underscore, users will depend on it — treat it as public even if you forgot to
  list it. Conversely, an underscore-prefixed name that leaks into examples has
  effectively become public; either support it or fix the examples.

Keep the public surface small. Every exported name is a promise you maintain
across every future release.

## The Deprecation Lifecycle

Removing something public is a three-phase process spanning a major version, so
users always have a working overlap window.

1. **Warn.** Keep the old thing working, but emit a `DeprecationWarning` that
   names the replacement (see the deprecation example in SKILL.md). The old and
   new APIs coexist. Do this in a minor release.
2. **Document.** Mark it deprecated in the docstring and docs, state the version
   it will be removed in, and show the migration. A user who reads the docs or
   sees the warning must be able to fix their code before removal.
3. **Remove.** Delete it — only in a major release, and only after the warning
   has shipped in a prior release users have had time to adopt.

```python
def old_encode(value):
    warnings.warn(
        "old_encode() is deprecated and will be removed in 3.0; use encode().",
        DeprecationWarning,
        stacklevel=2,
    )
    return encode(value)
```

Never skip straight from working to removed in a minor release, and never remove
something the same release you deprecated it. The warning window is the whole
point. `stacklevel=2` makes the warning point at the caller's line, not yours.

## Backward-Compatible Signature Changes

Most additions can be made without a breaking release if you shape them right.

**Add options as keyword-only with defaults.** A parameter after `*` can never
collide with an existing positional argument, so adding one is purely additive:

```python
# Before
def render(template, context):
    ...

# After — existing calls render(t, c) still work unchanged
def render(template, context, *, autoescape=True, cache=None):
    ...
```

**Use `*args` / `**kwargs` to accept more without committing to names**, e.g. to
pass through to a wrapped callable — but only where the extra arguments are
genuinely open-ended. Overusing them hides the real signature from users and
tools, so prefer explicit keyword-only parameters when you know the options.

**Deprecate a parameter with a sentinel** when you must change a default. A
plain new default is a breaking behavior change; route through a sentinel so you
can warn during the overlap window:

```python
_UNSET = object()

def fetch(url, *, verify=_UNSET):
    if verify is _UNSET:
        warnings.warn(
            "The default for verify will change to True in 4.0; "
            "pass verify explicitly to silence this.",
            DeprecationWarning, stacklevel=2,
        )
        verify = False
    ...
```

For the mutable-default-argument trap (`def f(x=[])`), see the `python-code-quality`
skill — it owns that anti-pattern.

## Feature-Flagging New Behavior

When new behavior would break existing users, ship it *off by default* behind an
opt-in flag, then flip the default in a later major release using the sentinel
deprecation above. This lets early adopters migrate on their own schedule while
the default stays stable.

```python
def parse(text, *, strict=False):
    """strict=True enables the stricter parser that will become the default in 5.0."""
    ...
```

Guidelines:

- Prefer a **keyword flag** on the relevant function over a global toggle; global
  mutable state makes behavior depend on import order and is hard to reason about.
- Name the flag for the behavior, not the version (`strict=`, not `v2_mode=`) —
  the flag outlives the version that introduced it.
- Plan the **retirement** of every flag. A flag that's permanently on-by-default
  is just a parameter; deprecate and remove the toggle once the transition is
  done, following the lifecycle above.
