import pytest

from pytest_clerk_mock import MockClerkClient


class TestOrganizationMembershipsCreate:
    """Tests for creating organization memberships."""

    def test_create_membership(self, mock_clerk: MockClerkClient) -> None:
        """Create membership returns membership with provided values."""

        membership = mock_clerk.organization_memberships.create(
            organization_id="org_123",
            user_id="user_456",
            role="org:member",
        )

        assert membership.id == "orgmem_org_123_user_456"
        assert membership.organization_id == "org_123"
        assert membership.user_id == "user_456"
        assert membership.role == "org:member"

    def test_create_membership_with_metadata(self, mock_clerk: MockClerkClient) -> None:
        """Create membership with metadata stores metadata correctly."""

        membership = mock_clerk.organization_memberships.create(
            organization_id="org_123",
            user_id="user_456",
            role="org:admin",
            public_metadata={"department": "engineering"},
            private_metadata={"salary_band": "L5"},
        )

        assert membership.public_metadata == {"department": "engineering"}
        assert membership.private_metadata == {"salary_band": "L5"}

    def test_create_membership_with_custom_role(self, mock_clerk: MockClerkClient) -> None:
        """Create membership with custom role."""

        membership = mock_clerk.organization_memberships.create(
            organization_id="org_123",
            user_id="user_456",
            role="org:billing_admin",
        )

        assert membership.role == "org:billing_admin"

    async def test_create_async(self, mock_clerk: MockClerkClient) -> None:
        """Async create works like sync version."""

        membership = await mock_clerk.organization_memberships.create_async(
            organization_id="org_async",
            user_id="user_async",
            role="org:member",
        )

        assert membership.id == "orgmem_org_async_user_async"
        assert membership.organization_id == "org_async"
        assert membership.user_id == "user_async"


class TestOrganizationMembershipsDelete:
    """Tests for deleting organization memberships."""

    def test_delete_membership(self, mock_clerk: MockClerkClient) -> None:
        """Delete removes membership and returns it."""

        mock_clerk.organization_memberships.create(
            organization_id="org_123",
            user_id="user_456",
            role="org:member",
        )

        deleted = mock_clerk.organization_memberships.delete(
            organization_id="org_123",
            user_id="user_456",
        )

        assert deleted is not None
        assert deleted.organization_id == "org_123"
        assert deleted.user_id == "user_456"

    def test_delete_nonexistent_returns_none(self, mock_clerk: MockClerkClient) -> None:
        """Delete nonexistent membership returns None."""

        result = mock_clerk.organization_memberships.delete(
            organization_id="org_nonexistent",
            user_id="user_nonexistent",
        )

        assert result is None

    async def test_delete_async(self, mock_clerk: MockClerkClient) -> None:
        """Async delete works like sync version."""

        await mock_clerk.organization_memberships.create_async(
            organization_id="org_async",
            user_id="user_async",
            role="org:member",
        )

        deleted = await mock_clerk.organization_memberships.delete_async(
            organization_id="org_async",
            user_id="user_async",
        )

        assert deleted is not None
        assert deleted.organization_id == "org_async"


class TestOrganizationMembershipsReset:
    """Tests for resetting organization memberships."""

    def test_reset_clears_memberships(self, mock_clerk: MockClerkClient) -> None:
        """Reset removes all memberships."""

        mock_clerk.organization_memberships.create(
            organization_id="org_1",
            user_id="user_1",
            role="org:member",
        )
        mock_clerk.organization_memberships.create(
            organization_id="org_2",
            user_id="user_2",
            role="org:admin",
        )

        mock_clerk.organization_memberships.reset()

        result1 = mock_clerk.organization_memberships.delete(
            organization_id="org_1",
            user_id="user_1",
        )
        result2 = mock_clerk.organization_memberships.delete(
            organization_id="org_2",
            user_id="user_2",
        )

        assert result1 is None
        assert result2 is None


class TestFixtureIsolation:
    """Tests that fixture resets between tests."""

    def test_fixture_isolation_first(self, mock_clerk: MockClerkClient) -> None:
        """First test creates a membership."""

        mock_clerk.organization_memberships.create(
            organization_id="org_isolation",
            user_id="user_isolation",
            role="org:member",
        )

        deleted = mock_clerk.organization_memberships.delete(
            organization_id="org_isolation",
            user_id="user_isolation",
        )

        assert deleted is not None

    def test_fixture_isolation_second(self, mock_clerk: MockClerkClient) -> None:
        """Second test sees empty store."""

        result = mock_clerk.organization_memberships.delete(
            organization_id="org_isolation",
            user_id="user_isolation",
        )

        assert result is None
