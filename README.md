# pytest-clerk-mock

A pytest plugin for mocking [Clerk](https://clerk.com/) authentication in your tests.

## Installation

```bash
pip install pytest-clerk-mock
```

Or with Poetry:

```bash
poetry add --group dev pytest-clerk-mock
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

    fetched = await mock_clerk.users.get_async(user_id=user.id)
    assert fetched.first_name == "John"
```

For SDK parity, several async methods are keyword-only (for example: `get_async(user_id=...)`, `update_async(user_id=...)`, `delete_async(user_id=...)`).

## Authentication

The mock client provides full authentication state management:

### Configure Auth State

```python
def test_with_auth(mock_clerk):
    mock_clerk.configure_auth("user_123", org_id="org_456", org_role="org:admin")

    result = mock_clerk.authenticate_request(request, options)
    assert result.is_signed_in
    assert result.payload["sub"] == "user_123"
```

### Temporary User Context

Use the `as_user` context manager to temporarily switch users:

```python
def test_as_different_user(mock_clerk):
    with mock_clerk.as_user("user_456", org_id="org_789"):
        result = mock_clerk.authenticate_request(request, options)
        assert result.payload["sub"] == "user_456"
```

### Predefined User Types

Use `MockClerkUser` for common test scenarios:

```python
from pytest_clerk_mock import MockClerkUser

def test_with_predefined_user(mock_clerk):
    with mock_clerk.as_clerk_user(MockClerkUser.TEAM_OWNER, org_id="org_123"):
        # Authenticated as team owner
        pass

    with mock_clerk.as_clerk_user(MockClerkUser.GUEST):
        # Authenticated as guest
        pass
```

Available predefined users:
- `MockClerkUser.TEAM_OWNER`
- `MockClerkUser.TEAM_MEMBER`
- `MockClerkUser.GUEST`
- `MockClerkUser.UNAUTHENTICATED`

## Organizations

```python
from clerk_backend_api.models import ClerkErrors

def test_organizations(mock_clerk):
    created = mock_clerk.organizations.create(
        name="My Organization",
        created_by="user_123",
        slug="my-org",
        private_metadata={"from_test": "e2e"},
    )

    org = mock_clerk.organizations.get(created.id)
    assert org.name == "My Organization"
    assert org.private_metadata["from_test"] == "e2e"

    with pytest.raises(ClerkErrors):
        mock_clerk.organizations.get("org_missing")
```

`add()` is still available as a lightweight helper when you want to seed a known org id directly in a test.

## Organization Memberships

Use the SDK-style `organization_memberships` API for org membership lifecycle:

```python
def test_organization_memberships(mock_clerk):
    membership = mock_clerk.organization_memberships.create(
        organization_id="org_123",
        user_id="user_123",
        role="org:admin",
    )

    assert membership.organization_id == "org_123"
    assert membership.user_id == "user_123"
    assert membership.role == "org:admin"

    memberships = mock_clerk.organization_memberships.list(
        organization_id="org_123",
        user_id=["user_123"],
    )
    assert memberships.total_count == 1
    assert memberships.data[0].user_id == "user_123"
```

If your app reads memberships via `users.get_organization_memberships(...)`, configure that explicitly:

```python
from pytest_clerk_mock import MockOrganizationMembershipsResponse

def test_user_membership_lookup(mock_clerk):
    mock_clerk.users.set_organization_memberships(
        "user_123",
        MockOrganizationMembershipsResponse(data=[], total_count=0),
    )
    memberships = mock_clerk.users.get_organization_memberships("user_123")
    assert memberships.total_count == 0
```

## Custom Fixture Configuration

Create a custom fixture with different defaults:

```python
# conftest.py
from pytest_clerk_mock import create_mock_clerk_fixture

mock_clerk = create_mock_clerk_fixture(
    default_user_id="user_custom",
    default_org_id="org_custom",
    default_org_role="org:member",
    autouse=True,
)
```

`patch_targets` is accepted for backward compatibility in fixture/context-manager helpers, but is deprecated and ignored.

## Context Manager API

For use outside of pytest fixtures:

```python
from pytest_clerk_mock import mock_clerk_backend

def test_with_context_manager():
    with mock_clerk_backend(default_user_id="user_123") as mock:
        mock.configure_auth("user_456")
        # Your test code here
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
| `get_organization_memberships()` | `get_organization_memberships_async()` |

### Organizations

| Sync | Async |
|------|-------|
| `add()` | - |
| `create()` | `create_async()` |
| `get()` | `get_async()` |
| `reset()` | - |

### Organization Memberships

| Sync | Async |
|------|-------|
| `create()` | `create_async()` |
| `list()` | `list_async()` |
| `delete()` | `delete_async()` |
| `reset()` | - |

### Authentication

| Method | Description |
|--------|-------------|
| `authenticate_request()` | Mock Clerk's authenticate_request |
| `configure_auth()` | Set current auth state |
| `configure_auth_from_user()` | Set auth using MockClerkUser |
| `as_user()` | Context manager for temporary user |
| `as_clerk_user()` | Context manager with MockClerkUser |
| `add_organization_membership()` | Add org membership for a user |
| `reset()` | Reset all mock state |

## Helper Functions

Low-level helpers for specific mocking scenarios:

```python
from pytest_clerk_mock import (
    create_clerk_errors,
    mock_clerk_user_creation,
    mock_clerk_user_creation_failure,
    mock_clerk_user_exists,
)

def test_user_creation():
    with mock_clerk_user_creation("myapp.clerk.users.create_async", "user_123") as mock:
        # Your code that creates a user
        mock.assert_called_once()

def test_creation_failure():
    with mock_clerk_user_creation_failure("myapp.clerk.users.create_async"):
        # Your code that handles creation failure
        pass

def test_duplicate_email():
    with mock_clerk_user_exists(
        "myapp.clerk.users.create_async",
        "myapp.clerk.users.list_async",
        "user_existing_123",
    ) as (mock_create, mock_list):
        # Your code that handles duplicate email scenario
        pass

def test_generic_clerk_error():
    err = create_clerk_errors()
    assert err is not None
```

## Exceptions

The mock raises appropriate exceptions matching Clerk's behavior:

- `ClerkErrors` - When creating a user with a duplicate email (matches real Clerk API)
- `ClerkErrors` - When getting/updating/deleting a non-existent user (uses `resource_not_found`)
- `ClerkErrors` - When getting a non-existent organization (uses `resource_not_found`)

```python
from clerk_backend_api.models import ClerkErrors

def test_user_not_found(mock_clerk):
    with pytest.raises(ClerkErrors):
        mock_clerk.users.get("nonexistent_user")

def test_duplicate_email(mock_clerk):
    mock_clerk.users.create(email_address=["test@example.com"])

    with pytest.raises(ClerkErrors):
        mock_clerk.users.create(email_address=["test@example.com"])
```

## License

MIT
