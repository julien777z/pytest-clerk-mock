from collections.abc import Generator
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from typing import Any
from unittest.mock import patch

import pytest

from pytest_clerk_mock.client import MockClerkClient

_current_mock_client: ContextVar[MockClerkClient | None] = ContextVar("_current_mock_client", default=None)


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


def _mock_organization_memberships_class(*args: Any, **kwargs: Any) -> _MockOrganizationMembershipsProxy:
    """Mock OrganizationMemberships class that returns the proxy."""

    return _organization_memberships_proxy


def _apply_sdk_patches(stack: ExitStack) -> None:
    """Apply Clerk SDK patches for the active mock client."""

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
    """Provide a patched mock Clerk client fixture."""

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
    default_user_id: str | None = "user_test_owner",
    default_org_id: str | None = "org_test_123",
    default_org_role: str = "org:admin",
) -> Generator[MockClerkClient, None, None]:
    """Provide a patched mock Clerk client context manager."""

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
    default_user_id: str | None = "user_test_owner",
    default_org_id: str | None = "org_test_123",
    default_org_role: str = "org:admin",
    autouse: bool = False,
):
    """Create a configured `mock_clerk` fixture."""

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
