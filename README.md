# pytest-mock-clerk

A pytest plugin for mocking [Clerk](https://clerk.com/) authentication in your tests.

## Installation

```bash
pip install pytest-mock-clerk
```

Or with Poetry:

```bash
poetry add --group dev pytest-mock-clerk
```

## Usage

The plugin provides a `mock_clerk` fixture that you can use in your tests:

```python
def test_create_user(mock_clerk):
    user = mock_clerk.users.create(
        email_address=["test@example.com"],
        first_name="John",
        last_name="Doe",
    )

    assert user.id is not None
    assert user.first_name == "John"

    fetched = mock_clerk.users.get(user.id)
    assert fetched.email_addresses[0].email_address == "test@example.com"
```

### Async API

All methods have async variants with an `_async` suffix, matching the clerk-backend-api SDK:

```python
async def test_create_user_async(mock_clerk):
    user = await mock_clerk.users.create_async(
        email_address=["test@example.com"],
        first_name="John",
        last_name="Doe",
    )

    assert user.id is not None

    fetched = await mock_clerk.users.get_async(user.id)
    assert fetched.first_name == "John"
```

## Supported Operations

### Users

| Sync | Async |
|------|-------|
| `create()` | `create_async()` |
| `get()` | `get_async()` |
| `list()` | `list_async()` |
| `update()` | `update_async()` |
| `delete()` | `delete_async()` |
| `count()` | `count_async()` |

## License

MIT
