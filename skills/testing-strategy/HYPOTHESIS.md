# Property-Based Testing with Hypothesis

## Installation

```bash
pip install hypothesis
```

## Basic Usage

```python
from hypothesis import given, strategies as st

@given(st.integers())
def test_integer_property(n):
    assert abs(n) >= 0

@given(st.text())
def test_string_roundtrip(s):
    assert decode(encode(s)) == s
```

## Common Strategies

```python
# Numbers
st.integers(min_value=0, max_value=100)
st.floats(min_value=-90, max_value=90)

# Text
st.text(min_size=1, max_size=100)
st.text(alphabet="abc123")

# Collections
st.lists(st.integers(), min_size=0, max_size=10)
st.dictionaries(st.text(), st.integers())

# Tuples
st.tuples(st.floats(), st.floats())

# Composite
@st.composite
def coordinates(draw):
    lat = draw(st.floats(min_value=-90, max_value=90))
    lon = draw(st.floats(min_value=-180, max_value=180))
    return (lat, lon)
```

## Filtering Invalid Data

```python
from hypothesis import assume

@given(st.floats())
def test_with_valid_floats(x):
    assume(not math.isnan(x))  # Skip NaN values
    assume(x != 0)              # Skip zero
    result = 1 / x
    assert math.isfinite(result)
```

## Settings

```python
from hypothesis import settings

@settings(max_examples=200)  # More thorough
@given(st.integers())
def test_thorough(n):
    ...

@settings(deadline=None)  # No time limit
@given(st.lists(st.integers()))
def test_slow_operation(items):
    ...
```

## Example: Roundtrip Testing

```python
@given(
    st.floats(min_value=-90, max_value=90, allow_nan=False),
    st.floats(min_value=-180, max_value=180, allow_nan=False),
)
def test_encode_decode_roundtrip(lat, lon):
    encoded = encode(lat, lon, precision=12)
    decoded_lat, decoded_lon = decode(encoded)
    assert abs(decoded_lat - lat) < 0.0001
    assert abs(decoded_lon - lon) < 0.0001
```
