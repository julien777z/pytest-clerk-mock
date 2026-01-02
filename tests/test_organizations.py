import pytest

from pytest_clerk_mock import (
    MockClerkClient,
    MockOrganization,
    OrganizationNotFoundError,
)


class TestMockOrganizationsClient:
    """Tests for MockOrganizationsClient."""

    async def test_add_and_get_organization(self, mock_clerk: MockClerkClient):
        """Test adding and retrieving an organization."""

        org = mock_clerk.organizations.add("org_123", name="Test Org", slug="test-org")

        assert org.id == "org_123"
        assert org.name == "Test Org"
        assert org.slug == "test-org"

        retrieved = mock_clerk.organizations.get("org_123")

        assert retrieved.id == "org_123"
        assert retrieved.name == "Test Org"

    async def test_get_nonexistent_organization_raises(
        self, mock_clerk: MockClerkClient
    ):
        """Test that getting a nonexistent organization raises an error."""

        with pytest.raises(OrganizationNotFoundError) as exc_info:
            mock_clerk.organizations.get("org_nonexistent")

        assert exc_info.value.organization_id == "org_nonexistent"

    async def test_get_async_organization(self, mock_clerk: MockClerkClient):
        """Test the async get method."""

        mock_clerk.organizations.add("org_async_test", name="Async Org")

        org = await mock_clerk.organizations.get_async("org_async_test")

        assert org.id == "org_async_test"
        assert org.name == "Async Org"

    async def test_reset_clears_organizations(self, mock_clerk: MockClerkClient):
        """Test that reset clears all organizations."""

        mock_clerk.organizations.add("org_1", name="Org 1")
        mock_clerk.organizations.add("org_2", name="Org 2")

        mock_clerk.organizations.reset()

        with pytest.raises(OrganizationNotFoundError):
            mock_clerk.organizations.get("org_1")

        with pytest.raises(OrganizationNotFoundError):
            mock_clerk.organizations.get("org_2")

    async def test_add_returns_mock_organization(self, mock_clerk: MockClerkClient):
        """Test that add returns a MockOrganization instance."""

        org = mock_clerk.organizations.add("org_type_test", name="Type Test")

        assert isinstance(org, MockOrganization)

    async def test_add_organization_with_defaults(self, mock_clerk: MockClerkClient):
        """Test adding an organization with default values."""

        org = mock_clerk.organizations.add("org_defaults")

        assert org.id == "org_defaults"
        assert org.name == ""
        assert org.slug == ""

