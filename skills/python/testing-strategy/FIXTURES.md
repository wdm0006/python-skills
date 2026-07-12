# Pytest Fixtures Reference

## Fixture Scopes

```python
@pytest.fixture  # function scope (default) - runs per test
@pytest.fixture(scope="class")    # per test class
@pytest.fixture(scope="module")   # per test file
@pytest.fixture(scope="session")  # once per test run
```

## Common Patterns

### Setup/Teardown

```python
@pytest.fixture
def database():
    conn = create_connection()
    yield conn  # Test runs here
    conn.close()  # Cleanup after test
```

### Factory Fixtures

```python
@pytest.fixture
def make_user():
    def _make_user(name="Test", email="test@example.com"):
        return User(name=name, email=email)
    return _make_user

def test_users(make_user):
    user1 = make_user(name="Alice")
    user2 = make_user(name="Bob")
```

### Temporary Files

```python
@pytest.fixture
def config_file(tmp_path):
    config = tmp_path / "config.json"
    config.write_text('{"key": "value"}')
    return config
```

### Mocking External Services

```python
@pytest.fixture
def mock_api(mocker):
    return mocker.patch(
        "my_lib.client.requests.get",
        return_value=Mock(json=lambda: {"data": []})
    )
```

## conftest.py

Shared fixtures go in `tests/conftest.py`:

```python
import pytest

@pytest.fixture
def sample_coordinates():
    return [
        (37.7749, -122.4194),
        (40.7128, -74.0060),
    ]
```

All tests in the directory can use these fixtures automatically.
