# pytest-clerk-mock

A pytest plugin for mocking [Clerk](https://clerk.com/) auth plus the supported Clerk backend SDK clients.

Supported SDK surfaces:

- `users`
- `organizations`
- `organization_memberships`

The plugin patches Clerk at the SDK level, so it works even if your app instantiates its Clerk client before the test runs.

## Installation

```bash
pip install pytest-clerk-mock
```

Or with Poetry:

```bash
poetry add --group dev pytest-clerk-mock
```

## Quick Start

```python
def test_create_user(mock_clerk):
    user = mock_clerk.users.create(
        email_address=["test@example.com"],
        first_name="John",
        last_name="Doe",
    )

    fetched = mock_clerk.users.get(user_id=user.id)

    assert fetched.email_addresses[0].email_address == "test@example.com"
```

Async methods use Clerk-style signatures too:

```python
async def test_create_user_async(mock_clerk):
    user = await mock_clerk.users.create_async(email_address=["test@example.com"])
    fetched = await mock_clerk.users.get_async(user_id=user.id)

    assert fetched.id == user.id
```

## Auth Helpers

```python
def test_auth(mock_clerk, request, options):
    mock_clerk.configure_auth("user_123", org_id="org_456", org_role="org:admin")

    result = mock_clerk.authenticate_request(request, options)

    assert result.is_signed_in
```

Temporary auth context:

```python
with mock_clerk.as_user("user_456", org_id="org_789"):
    ...
```

Predefined users:

- `MockClerkUser.TEAM_OWNER`
- `MockClerkUser.TEAM_MEMBER`
- `MockClerkUser.GUEST`
- `MockClerkUser.UNAUTHENTICATED`

## Common Examples

Organizations:

```python
created = mock_clerk.organizations.create(
    request={
        "name": "My Organization",
        "created_by": "user_123",
        "slug": "my-org",
    }
)

org = mock_clerk.organizations.get(organization_id=created.id)
```

Organization memberships:

```python
membership = mock_clerk.organization_memberships.create(
    organization_id="org_123",
    user_id="user_123",
    role="org:admin",
)
```

If your app reads memberships through `users.get_organization_memberships(...)`, seed them explicitly:

```python
from pytest_clerk_mock import MockOrganizationMembershipsResponse

mock_clerk.users.set_organization_memberships(
    "user_123",
    MockOrganizationMembershipsResponse(data=[], total_count=0),
)
```

## Scope

This package aims for strong parity for the supported Clerk SDK surfaces above. It does **not** try to mock every Clerk API domain.

The contract tests and CI job are the source of truth for supported method and model parity.

## Test Helpers

Useful non-SDK helpers:

- `mock_clerk.users.set_organization_memberships(...)`
- `mock_clerk.organizations.add(...)`
- `mock_clerk.organization_memberships.get(...)`

Custom fixture:

```python
from pytest_clerk_mock import create_mock_clerk_fixture

mock_clerk = create_mock_clerk_fixture(
    default_user_id="user_custom",
    default_org_id="org_custom",
    default_org_role="org:member",
    autouse=True,
)
```

Context manager:

```python
from pytest_clerk_mock import mock_clerk_backend

with mock_clerk_backend(default_user_id="user_123") as mock:
    mock.configure_auth("user_456")
```

Low-level patch helpers:

```python
from pytest_clerk_mock import (
    create_clerk_errors,
    mock_clerk_user_creation,
    mock_clerk_user_creation_failure,
    mock_clerk_user_exists,
)
```

## License

MIT
