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
        """Mock implementation of Clerk's authenticate_request.

        Args:
            request: The FastAPI/Starlette request object (ignored in mock)
            options: AuthenticateRequestOptions (ignored in mock)

        Returns:
            MockAuthResult with current auth state
        """

        return self._auth_state.get_result()

    def configure_auth(
        self,
        user_id: str | None,
        org_id: str | None = None,
        org_role: str = "org:admin",
    ) -> None:
        """Configure the authentication state.

        Args:
            user_id: The user ID to return in auth results (None for unauthenticated)
            org_id: The organization ID for the authenticated user
            org_role: The role of the user in the organization
        """

        self._auth_state.configure(user_id, org_id, org_role)

    def configure_auth_from_user(
        self,
        user: MockClerkUser,
        org_id: str | None = None,
        org_role: str = "org:admin",
    ) -> None:
        """Configure auth state using a predefined MockClerkUser.

        Args:
            user: The MockClerkUser enum value
            org_id: The organization ID for the authenticated user
            org_role: The role of the user in the organization
        """

        self._auth_state.configure(user.value, org_id, org_role)

    @contextmanager
    def as_user(
        self,
        user_id: str | None,
        org_id: str | None = None,
        org_role: str = "org:admin",
    ) -> Generator[None, None, None]:
        """Context manager to temporarily switch to a different user.

        Args:
            user_id: The user ID to use within the context
            org_id: The organization ID for the user
            org_role: The role of the user in the organization

        Yields:
            None

        Example:
            with mock_clerk.as_user("user_123", org_id="org_456"):
                # Requests will be authenticated as user_123
                pass
        """

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
        """Context manager using predefined MockClerkUser.

        Args:
            user: The MockClerkUser enum value
            org_id: The organization ID for the user
            org_role: The role of the user in the organization

        Example:
            with mock_clerk.as_clerk_user(MockClerkUser.TEAM_OWNER, org_id="org_123"):
                # Requests will be authenticated as team owner
                pass
        """

        with self.as_user(user.value, org_id, org_role):
            yield

    def add_organization_membership(
        self,
        user_id: str,
        org_id: str,
        role: str = "org:member",
        org_name: str = "",
    ) -> MockOrganizationMembership:
        """Add an organization membership for a user.

        Args:
            user_id: The user ID to add membership for
            org_id: The organization ID
            role: The role in the organization
            org_name: Optional organization name

        Returns:
            The created membership
        """

        membership = MockOrganizationMembership(
            id=f"orgmem_{user_id}_{org_id}",
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
