from collections.abc import Generator
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from typing import Any
from unittest.mock import patch

import pytest

from pytest_clerk_mock.client import MockClerkClient

_current_mock_client: ContextVar[MockClerkClient | None] = ContextVar(
    "_current_mock_client", default=None
)


def _get_current_client() -> MockClerkClient:
    """Get the current MockClerkClient from context."""

    client = _current_mock_client.get()

    if client is None:
        raise RuntimeError("No MockClerkClient is currently active")

    return client


def _mock_authenticate_request(request: Any, options: Any) -> Any:
    """Mock authenticate_request function that delegates to the current mock client."""

    return _get_current_client().authenticate_request(request, options)


class _MockUsersProxy:
    """Proxy that delegates all calls to the current mock client's users."""

    def __getattr__(self, name: str) -> Any:
        return getattr(_get_current_client().users, name)


_users_proxy = _MockUsersProxy()


def _mock_users_class(*args: Any, **kwargs: Any) -> _MockUsersProxy:
    """Mock Users class that returns the proxy."""

    return _users_proxy


class _MockOrganizationsProxy:
    """Proxy that delegates all calls to the current mock client's organizations."""

    def __getattr__(self, name: str) -> Any:
        return getattr(_get_current_client().organizations, name)


_organizations_proxy = _MockOrganizationsProxy()


def _mock_organizations_class(*args: Any, **kwargs: Any) -> _MockOrganizationsProxy:
    """Mock Organizations class that returns the proxy."""

    return _organizations_proxy


class _MockOrganizationMembershipsProxy:
    """Proxy that delegates all calls to the current mock client's organization_memberships."""

    def __getattr__(self, name: str) -> Any:
        return getattr(_get_current_client().organization_memberships, name)


_organization_memberships_proxy = _MockOrganizationMembershipsProxy()


def _mock_organization_memberships_class(
    *args: Any, **kwargs: Any
) -> _MockOrganizationMembershipsProxy:
    """Mock OrganizationMemberships class that returns the proxy."""

    return _organization_memberships_proxy


def _apply_sdk_patches(stack: ExitStack) -> None:
    """Apply patches to clerk_backend_api SDK internals.

    This patches at the SDK level so it works regardless of when/how
    the Clerk client was instantiated.
    """

    stack.enter_context(
        patch(
            "clerk_backend_api.security.authenticaterequest.authenticate_request",
            _mock_authenticate_request,
        )
    )

    stack.enter_context(
        patch(
            "clerk_backend_api.security.authenticate_request",
            _mock_authenticate_request,
        )
    )

    stack.enter_context(
        patch(
            "clerk_backend_api.sdk.authenticate_request",
            _mock_authenticate_request,
        )
    )

    stack.enter_context(
        patch(
            "clerk_backend_api.users.Users",
            _mock_users_class,
        )
    )

    stack.enter_context(
        patch(
            "clerk_backend_api.organizations_sdk.OrganizationsSDK",
            _mock_organizations_class,
        )
    )

    stack.enter_context(
        patch(
            "clerk_backend_api.organizationmemberships_sdk.OrganizationMembershipsSDK",
            _mock_organization_memberships_class,
        )
    )


@pytest.fixture
def mock_clerk() -> Generator[MockClerkClient, None, None]:
    """Fixture that provides a mock Clerk client.

    The client is reset after each test to ensure isolation.
    Patches clerk_backend_api SDK internals to intercept all Clerk operations.

    Yields:
        MockClerkClient instance configured with default auth state.

    Example:
        def test_something(mock_clerk):
            # Configure auth state
            mock_clerk.configure_auth("user_123", "org_456")

            # Or use context manager for temporary user switch
            with mock_clerk.as_user("user_456", "org_789"):
                # Test as different user
                pass
    """

    client = MockClerkClient()
    token = _current_mock_client.set(client)

    with ExitStack() as stack:
        _apply_sdk_patches(stack)
        stack.enter_context(patch("clerk_backend_api.Clerk", return_value=client))

        yield client

    _current_mock_client.reset(token)
    client.reset()


@contextmanager
def mock_clerk_backend(
    patch_targets: list[str] | None = None,
    default_user_id: str | None = "user_test_owner",
    default_org_id: str | None = "org_test_123",
    default_org_role: str = "org:admin",
) -> Generator[MockClerkClient, None, None]:
    """Context manager for mocking Clerk backend.

    This provides a moto-like API for mocking Clerk in tests without using fixtures.
    Patches clerk_backend_api SDK internals so it works regardless of when the
    Clerk client was instantiated.

    Args:
        patch_targets: Deprecated. No longer needed - SDK is patched at the internal level.
        default_user_id: Default user ID for authentication (None for unauthenticated)
        default_org_id: Default organization ID
        default_org_role: Default organization role

    Yields:
        MockClerkClient instance

    Example:
        with mock_clerk_backend() as mock:
            mock.configure_auth("user_123", "org_456")
            # Your test code here
    """

    del patch_targets

    client = MockClerkClient(
        default_user_id=default_user_id,
        default_org_id=default_org_id,
        default_org_role=default_org_role,
    )
    token = _current_mock_client.set(client)

    with ExitStack() as stack:
        _apply_sdk_patches(stack)
        stack.enter_context(patch("clerk_backend_api.Clerk", return_value=client))

        yield client

    _current_mock_client.reset(token)
    client.reset()


def create_mock_clerk_fixture(
    patch_targets: list[str] | None = None,
    default_user_id: str | None = "user_test_owner",
    default_org_id: str | None = "org_test_123",
    default_org_role: str = "org:admin",
    autouse: bool = False,
):
    """Factory function to create a mock_clerk fixture with custom configuration.

    Patches clerk_backend_api SDK internals so it works regardless of when the
    Clerk client was instantiated.

    Args:
        patch_targets: Deprecated. No longer needed - SDK is patched at the internal level.
        default_user_id: Default user ID for authentication
        default_org_id: Default organization ID
        default_org_role: Default organization role
        autouse: Whether to automatically use the fixture in all tests

    Returns:
        A pytest fixture function

    Example:
        # In conftest.py
        from pytest_clerk_mock import create_mock_clerk_fixture

        mock_clerk = create_mock_clerk_fixture(autouse=True)
    """

    del patch_targets

    @pytest.fixture(autouse=autouse)
    def custom_mock_clerk() -> Generator[MockClerkClient, None, None]:
        client = MockClerkClient(
            default_user_id=default_user_id,
            default_org_id=default_org_id,
            default_org_role=default_org_role,
        )
        token = _current_mock_client.set(client)

        with ExitStack() as stack:
            _apply_sdk_patches(stack)
            stack.enter_context(patch("clerk_backend_api.Clerk", return_value=client))

            yield client

        _current_mock_client.reset(token)
        client.reset()

    return custom_mock_clerk
