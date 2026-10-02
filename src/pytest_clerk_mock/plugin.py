from collections.abc import Callable, Generator
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from typing import Any, Final
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


SDK_SERVICE_CLASSES: Final[dict[str, str]] = {
    "clerk_backend_api.users.Users": "users",
    "clerk_backend_api.organizations_sdk.OrganizationsSDK": "organizations",
    "clerk_backend_api.organizationmemberships_sdk.OrganizationMembershipsSDK": "organization_memberships",
    "clerk_backend_api.emailaddresses.EmailAddresses": "email_addresses",
    "clerk_backend_api.actortokens.ActorTokens": "actor_tokens",
    "clerk_backend_api.sessions.Sessions": "sessions",
}


class ServiceProxy:
    """Proxy that delegates every call to one service of the current mock client."""

    def __init__(self, service: str) -> None:
        self.service = service

    def __getattr__(self, name: str) -> Any:
        return getattr(getattr(_get_current_client(), self.service), name)


def mock_service_class(service: str) -> Callable[..., ServiceProxy]:
    """Build a stand-in for an SDK service class that returns a proxy to the mock service."""

    proxy = ServiceProxy(service)

    def _construct(*args: Any, **kwargs: Any) -> ServiceProxy:
        """Return the proxy whatever the SDK passes its service class."""

        return proxy

    return _construct


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

    for service_class, service in SDK_SERVICE_CLASSES.items():
        stack.enter_context(patch(service_class, mock_service_class(service)))


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
