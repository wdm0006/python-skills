# Type Hint Patterns Reference

## Basic Types

```python
from collections.abc import Sequence, Mapping, Callable, Iterator

# Primitives
x: int = 1
y: str = "hello"
z: bool = True

# Collections
items: list[str] = []
mapping: dict[str, int] = {}
coords: tuple[float, float] = (0.0, 0.0)

# Optional
name: str | None = None
```

## Function Signatures

```python
# Basic
def greet(name: str) -> str:
    return f"Hello, {name}"

# Multiple returns
def parse(s: str) -> tuple[int, str]:
    ...

# Keyword-only after *
def fetch(url: str, *, timeout: int = 30) -> bytes:
    ...

# Callable parameter
def apply(func: Callable[[int], str], value: int) -> str:
    return func(value)
```

## Generics

```python
from typing import TypeVar, Generic

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")

def first(items: Sequence[T]) -> T | None:
    return items[0] if items else None

class Cache(Generic[K, V]):
    def __init__(self) -> None:
        self._data: dict[K, V] = {}

    def get(self, key: K) -> V | None:
        return self._data.get(key)

    def set(self, key: K, value: V) -> None:
        self._data[key] = value
```

## Protocols (Structural Typing)

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Encoder(Protocol):
    def encode(self, data: bytes) -> str: ...
    def decode(self, text: str) -> bytes: ...

# Any class with encode/decode methods satisfies Encoder
def process(encoder: Encoder, data: bytes) -> str:
    return encoder.encode(data)
```

## Type Aliases

```python
from typing import TypeAlias

Coordinate: TypeAlias = tuple[float, float]
BoundingBox: TypeAlias = tuple[float, float, float, float]
Handler: TypeAlias = Callable[[str], None]

def process(coord: Coordinate, box: BoundingBox) -> None:
    ...
```

## Overloads

```python
from typing import overload

@overload
def get(key: str) -> str: ...
@overload
def get(key: str, default: str) -> str: ...
@overload
def get(key: str, default: None) -> str | None: ...

def get(key: str, default: str | None = None) -> str | None:
    ...
```

## TypedDict

```python
from typing import TypedDict, Required, NotRequired

class Config(TypedDict):
    name: str                    # Required
    version: str                 # Required
    debug: NotRequired[bool]     # Optional

def load_config() -> Config:
    return {"name": "app", "version": "1.0"}
```
