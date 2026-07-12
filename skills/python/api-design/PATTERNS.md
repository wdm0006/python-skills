# API Design Patterns

Concrete patterns for building intuitive Python library APIs. Applies the core
principles (simplicity, consistency, least surprise, discoverability) to specific
design decisions.

## Contents

- [Keyword-Only Arguments](#keyword-only-arguments)
- [Config Objects vs Fluent Builders](#config-objects-vs-fluent-builders)
- [Factory Functions vs Classmethods](#factory-functions-vs-classmethods)
- [Context Managers for Resource Lifecycle](#context-managers-for-resource-lifecycle)
- [Protocols and Duck Typing](#protocols-and-duck-typing)
- [Sensible Defaults and Progressive Disclosure](#sensible-defaults-and-progressive-disclosure)
- [Structured Return Types](#structured-return-types)
- [Exception Hierarchy Design](#exception-hierarchy-design)

## Keyword-Only Arguments

Force callers to name options so call sites stay readable and signatures stay
free to evolve. Put everything after `*` that isn't an obvious positional.

```python
# Bad: boolean trap, order-dependent, unreadable at the call site
def connect(host, 5432, True, False, 30):
    ...

# Good: one clear positional, the rest keyword-only
def connect(host: str, *, port: int = 5432, tls: bool = True,
            retry: bool = False, timeout: float = 30.0) -> Connection:
    ...

connect("db.internal", port=6432, tls=True, timeout=5.0)
```

Keyword-only options are also the safest to add later: a new `*, verbose=False`
never shifts an existing positional. Reserve positional slots for the one or two
arguments a caller could never confuse (the subject of the verb).

## Config Objects vs Fluent Builders

When options grow past a handful, group them instead of ballooning the
signature. Two idiomatic shapes:

**Config object (dataclass)** — a plain, inspectable value. Prefer this. It is
easy to construct, compare, serialize, and pass around.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class RetryPolicy:
    attempts: int = 3
    backoff: float = 0.5
    jitter: bool = True

client = Client(retry=RetryPolicy(attempts=5))
```

**Fluent builder** — chained calls returning `self` (or a new immutable copy).
Reach for it only when construction is genuinely stepwise or conditional. Return
a *new* instance from each step so a half-built builder can't leak shared state.

```python
query = (
    Query.select("id", "name")
    .where(active=True)
    .order_by("name")
    .limit(50)
)
```

Prefer config objects by default; a fluent builder earns its keep only when the
chaining reads better than a single constructor call. Don't offer both for the
same thing.

## Factory Functions vs Classmethods

Both create instances without exposing a cluttered `__init__`. Choose by whose
name reads better at the call site.

Use a **classmethod** for an alternate constructor of a known type — the class
name adds context:

```python
class Image:
    @classmethod
    def from_bytes(cls, data: bytes) -> "Image": ...
    @classmethod
    def from_path(cls, path: str) -> "Image": ...

Image.from_path("logo.png")
```

Use a **module-level factory function** when the caller shouldn't need to know
the concrete class, or when the return type varies:

```python
def open_store(url: str) -> Store:
    """Return a RedisStore, S3Store, or MemoryStore based on the URL scheme."""
    ...

store = open_store("redis://localhost")  # concrete type is an implementation detail
```

Keep `__init__` as the plain "I already have all the fields" path; layer named
constructors on top for the common ways users actually start.

## Context Managers for Resource Lifecycle

Anything that must be released — connections, files, locks, transactions,
temporary state — should be a context manager so cleanup can't be forgotten.

```python
from contextlib import contextmanager

@contextmanager
def transaction(conn):
    tx = conn.begin()
    try:
        yield tx
        tx.commit()
    except Exception:
        tx.rollback()
        raise

with transaction(conn) as tx:
    tx.execute(...)   # commits on success, rolls back on error
```

Offer the `with` form as the primary API. If you also expose manual
`open()`/`close()`, make the object usable both ways (implement `__enter__`/
`__exit__`) rather than forcing one style.

## Protocols and Duck Typing

Extend a library by defining the *shape* callers must satisfy, not a base class
they must inherit. `typing.Protocol` documents that shape and type-checks it
without coupling users to your hierarchy.

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Serializer(Protocol):
    def dumps(self, obj: object) -> bytes: ...
    def loads(self, data: bytes) -> object: ...

def save(obj: object, *, serializer: Serializer) -> bytes:
    return serializer.dumps(obj)
```

Any object with matching methods works — including ones the user wrote and
third-party types you've never seen. Accept the protocol; don't demand a
subclass. Reserve abstract base classes for cases where you must share
implementation, not merely an interface.

## Sensible Defaults and Progressive Disclosure

Every parameter that can have a good default should have one, so the zero-config
call does the right thing. Layer power on top for those who need it (see the
progressive disclosure pattern in SKILL.md).

```python
# The 90% call is trivial...
tokens = tokenize(text)

# ...and the knobs exist when needed, without changing the simple path.
tokens = tokenize(text, *, lowercase=False, max_len=512, strip_accents=True)
```

Defaults should encode the safest, most common intent. A caller who reads only
the function name and its first argument should still get correct behavior.

## Structured Return Types

Returning a bare tuple or dict forces callers to remember index order or string
keys, and quietly breaks them when you add a field. Return a named type.

```python
# Bad: what is [2]? what keys exist? adding a field shifts every index.
def parse(url): return (scheme, host, port, path)

# Good: self-documenting, autocompletes, extensible
from typing import NamedTuple

class ParsedURL(NamedTuple):
    scheme: str
    host: str
    port: int
    path: str

result = parse("https://x.com/y")
result.host        # clear at the call site
scheme, host, *_ = result   # still unpacks if the caller wants tuples
```

Use a `NamedTuple` when positional unpacking is a feature; use a `@dataclass`
when the result is a richer object with methods or mutability. Either way,
adding a field is backward compatible in a way that tuple indices and dict keys
are not.

## Exception Hierarchy Design

Give the library a single base exception so callers can catch everything from it
with one `except`, then subclass for specific, catchable failures.

```python
class LibraryError(Exception):
    """Base for every error this library raises."""

class ValidationError(LibraryError):
    """Input failed validation."""

class ConnectionError(LibraryError):
    """Could not reach the backend."""

class TimeoutError(ConnectionError):
    """A connection attempt exceeded its deadline."""
```

Rules that keep the hierarchy useful:

- **Everything raised inherits from `LibraryError`.** Callers can write
  `except LibraryError` and know they've contained your library.
- **Subclass by what the caller will do about it**, not by where it was thrown.
  If two errors are always handled identically, they can be one class.
- **Subclass built-ins when the semantics genuinely match** (e.g. inherit from
  both `LibraryError` and `ValueError`) so existing `except ValueError` handlers
  keep working — but keep `LibraryError` in the bases.
- **Attach context** (offending value, hint) as in the SKILL.md error-handling
  example, rather than baking everything into the message string.

Never raise a bare `Exception` or a naked built-in from library code — it gives
callers nothing specific to catch and nothing shared to catch broadly.
