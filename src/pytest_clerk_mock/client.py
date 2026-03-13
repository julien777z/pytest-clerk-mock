from contextlib import contextmanager
from typing import Any, Generator

from pytest_clerk_mock.models.auth import MockAuthResult, MockClerkUser
from pytest_clerk_mock.models.organization import (
    MockOrganization,
    MockOrganizationMembership,
    MockOrganizationMembershipsResponse,
)
from pytest_clerk_mock.services.auth import MockAuthState
from pytest_clerk_mock.services.organization_memberships import (
    MockOrganizationMembershipsClient,
)
from pytest_clerk_mock.services.organizations import MockOrganizationsClient
from pytest_clerk_mock.services.users import MockUsersClient
from pytest_clerk_mock.utils import generate_clerk_id


class MockClerkClient:
    """Mock implementation of Clerk's SDK client."""

    def __init__(
        self,
        default_user_id: str | None = "user_test_owner",
        default_org_id: str | None = "org_test_123",
        default_org_role: str = "org:admin",
    ) -> None:
        self._users = MockUsersClient()
        self._organizations = MockOrganizationsClient()
        self._organization_memberships = MockOrganizationMembershipsClient()
        self._auth_state = MockAuthState()
        self._memberships: dict[str, list[MockOrganizationMembership]] = {}

        if default_user_id is not None:
            self._auth_state.configure(default_user_id, default_org_id, default_org_role)

    @property
    def users(self) -> MockUsersClient:
        """Access the Users API."""

        return self._users

    @property
    def organizations(self) -> MockOrganizationsClient:
        """Access the Organizations API."""

        return self._organizations

    @property
    def organization_memberships(self) -> MockOrganizationMembershipsClient:
        """Access the OrganizationMemberships API."""

        return self._organization_memberships

    def reset(self) -> None:
        """Reset all mock services."""

        self._users.reset()
        self._organizations.reset()
        self._organization_memberships.reset()
        self._auth_state.reset()
        self._memberships.clear()

    def authenticate_request(
        self,
        request: Any,
        options: Any = None,
    ) -> MockAuthResult:
        """Return the current mock authentication result."""

        return self._auth_state.get_result()

    def configure_auth(
        self,
        user_id: str | None,
        org_id: str | None = None,
        org_role: str = "org:admin",
    ) -> None:
        """Configure the active authentication state."""

        self._auth_state.configure(user_id, org_id, org_role)

    def configure_auth_from_user(
        self,
        user: MockClerkUser,
        org_id: str | None = None,
        org_role: str = "org:admin",
    ) -> None:
        """Configure authentication state from a predefined mock user."""

        self._auth_state.configure(user.value, org_id, org_role)

    @contextmanager
    def as_user(
        self,
        user_id: str | None,
        org_id: str | None = None,
        org_role: str = "org:admin",
    ) -> Generator[None, None, None]:
        """Temporarily switch authentication state to another user."""

        previous = self._auth_state.snapshot()
        self._auth_state.configure(user_id, org_id, org_role)

        try:
            yield
        finally:
            self._auth_state.restore(previous)

    @contextmanager
    def as_clerk_user(
        self,
        user: MockClerkUser,
        org_id: str | None = None,
        org_role: str = "org:admin",
    ) -> Generator[None, None, None]:
        """Temporarily switch authentication state to a predefined mock user."""

        with self.as_user(user.value, org_id, org_role):
            yield

    def add_organization_membership(
        self,
        user_id: str,
        org_id: str,
        role: str = "org:member",
        org_name: str = "",
    ) -> MockOrganizationMembership:
        """Add an organization membership for a user."""

        membership = MockOrganizationMembership(
            id=generate_clerk_id("orgmem"),
            role=role,
            organization=MockOrganization(id=org_id, name=org_name),
        )

        if user_id not in self._memberships:
            self._memberships[user_id] = []

        self._memberships[user_id].append(membership)

        return membership

    async def _get_organization_memberships_async(
        self,
        user_id: str,
    ) -> MockOrganizationMembershipsResponse:
        """Get organization memberships for a user (internal async method)."""

        memberships = self._memberships.get(user_id, [])

        return MockOrganizationMembershipsResponse(
            data=memberships,
            total_count=len(memberships),
        )
