from typing import Any

from pytest_clerk_mock.models.organization import MockOrganizationMembership


class MockOrganizationMembershipsClient:
    """Mock implementation of Clerk's OrganizationMemberships API."""

    def __init__(self) -> None:
        self._memberships: dict[str, MockOrganizationMembership] = {}

    def reset(self) -> None:
        """Clear all stored memberships."""

        self._memberships.clear()

    def _make_key(self, organization_id: str, user_id: str) -> str:
        """Create a unique key for a membership."""

        return f"{organization_id}:{user_id}"

    def create(
        self,
        *,
        organization_id: str,
        user_id: str,
        role: str,
        public_metadata: dict[str, Any] | None = None,
        private_metadata: dict[str, Any] | None = None,
    ) -> MockOrganizationMembership:
        """Create a new organization membership."""

        key = self._make_key(organization_id, user_id)
        membership = MockOrganizationMembership(
            id=f"orgmem_{organization_id}_{user_id}",
            organization_id=organization_id,
            user_id=user_id,
            role=role,
            public_metadata=public_metadata or {},
            private_metadata=private_metadata or {},
        )
        self._memberships[key] = membership

        return membership

    async def create_async(
        self,
        *,
        organization_id: str,
        user_id: str,
        role: str,
        public_metadata: dict[str, Any] | None = None,
        private_metadata: dict[str, Any] | None = None,
    ) -> MockOrganizationMembership:
        """Async version of create."""

        return self.create(
            organization_id=organization_id,
            user_id=user_id,
            role=role,
            public_metadata=public_metadata,
            private_metadata=private_metadata,
        )

    def get(
        self,
        *,
        organization_id: str,
        user_id: str,
    ) -> MockOrganizationMembership | None:
        """Get a membership by organization and user ID."""

        key = self._make_key(organization_id, user_id)

        return self._memberships.get(key)

    def delete(
        self,
        *,
        organization_id: str,
        user_id: str,
    ) -> MockOrganizationMembership | None:
        """Delete a membership."""

        key = self._make_key(organization_id, user_id)

        return self._memberships.pop(key, None)

    async def delete_async(
        self,
        *,
        organization_id: str,
        user_id: str,
    ) -> MockOrganizationMembership | None:
        """Async version of delete."""

        return self.delete(organization_id=organization_id, user_id=user_id)
