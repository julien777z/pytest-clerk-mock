import pytest
from clerk_backend_api.models import ClerkErrors

from pytest_clerk_mock import (
    MockClerkClient,
    MockOrganization,
)

RESOURCE_NOT_FOUND_CODE = "resource_not_found"


def _assert_resource_not_found(exc: ClerkErrors, *, organization_id: str) -> None:
    """Assert ClerkErrors contains a resource_not_found organization error."""

    errors = exc.data.errors
    assert len(errors) == 1
    assert errors[0].code == RESOURCE_NOT_FOUND_CODE
    assert errors[0].message == f"Organization not found: {organization_id}"


class TestOrganizationAdd:
    """Tests for adding organizations."""

    def test_add_organization(self, mock_clerk: MockClerkClient) -> None:
        """Add creates organization with provided values."""

        org = mock_clerk.organizations.add("org_123", name="Test Org", slug="test-org")

        assert org.id == "org_123"
        assert org.name == "Test Org"
        assert org.slug == "test-org"

    def test_add_returns_mock_organization(self, mock_clerk: MockClerkClient) -> None:
        """Add returns a MockOrganization instance."""

        org = mock_clerk.organizations.add("org_type_test", name="Type Test")

        assert isinstance(org, MockOrganization)

    def test_add_with_defaults(self, mock_clerk: MockClerkClient) -> None:
        """Add uses empty strings for optional fields."""

        org = mock_clerk.organizations.add("org_defaults")

        assert org.id == "org_defaults"
        assert org.name == ""
        assert org.slug == ""


class TestOrganizationCreate:
    """Tests for creating organizations."""

    def test_create_organization(self, mock_clerk: MockClerkClient) -> None:
        """Test that create generates an organization id and stores Clerk-style fields."""

        org = mock_clerk.organizations.create(
            request={
                "name": "Created Org",
                "created_by": "user_creator",
                "slug": "created-org",
                "public_metadata": {"team": "platform"},
                "private_metadata": {"from_test": "e2e"},
                "max_allowed_memberships": 25,
            }
        )

        assert org.id.startswith("org_")
        assert org.name == "Created Org"
        assert org.created_by == "user_creator"
        assert org.slug == "created-org"
        assert org.public_metadata == {"team": "platform"}
        assert org.private_metadata == {"from_test": "e2e"}
        assert org.max_allowed_memberships == 25

    async def test_create_async_with_request(self, mock_clerk: MockClerkClient) -> None:
        """Test that create_async accepts the Clerk-style request payload used in app tests."""

        org = await mock_clerk.organizations.create_async(
            request={
                "name": "Async Org",
                "created_by": "user_async_creator",
                "slug": "async-org",
                "public_metadata": {"team": "backend"},
                "private_metadata": {"from_test": "e2e"},
            }
        )

        stored = mock_clerk.organizations.get(org.id)

        assert stored.id.startswith("org_")
        assert stored.name == "Async Org"
        assert stored.created_by == "user_async_creator"
        assert stored.slug == "async-org"
        assert stored.public_metadata == {"team": "backend"}
        assert stored.private_metadata == {"from_test": "e2e"}

    async def test_create_async_with_full_request_payload(self, mock_clerk: MockClerkClient) -> None:
        """Test that create_async accepts the full supported request payload."""

        org = await mock_clerk.organizations.create_async(
            request={
                "name": "Request Org",
                "created_by": "user_request_creator",
                "slug": "request-org",
                "public_metadata": {"team": "platform"},
                "private_metadata": {"source": "object"},
                "max_allowed_memberships": 10,
                "created_at": "2026-03-12T00:00:00Z",
            }
        )
        stored = mock_clerk.organizations.get(org.id)

        assert stored.id.startswith("org_")
        assert stored.name == "Request Org"
        assert stored.created_by == "user_request_creator"
        assert stored.slug == "request-org"
        assert stored.public_metadata == {"team": "platform"}
        assert stored.private_metadata == {"source": "object"}
        assert stored.max_allowed_memberships == 10


class TestOrganizationGet:
    """Tests for getting organizations."""

    def test_get_organization(self, mock_clerk: MockClerkClient) -> None:
        """Get returns the added organization."""

        mock_clerk.organizations.add("org_123", name="Test Org")

        retrieved = mock_clerk.organizations.get("org_123")

        assert retrieved.id == "org_123"
        assert retrieved.name == "Test Org"

    def test_get_not_found(self, mock_clerk: MockClerkClient) -> None:
        """Nonexistent organization raises ClerkErrors."""

        with pytest.raises(ClerkErrors) as exc_info:
            mock_clerk.organizations.get("org_nonexistent")

        _assert_resource_not_found(exc_info.value, organization_id="org_nonexistent")

    async def test_get_async(self, mock_clerk: MockClerkClient) -> None:
        """Async get returns added organization."""

        mock_clerk.organizations.add("org_async_test", name="Async Org")

        org = await mock_clerk.organizations.get_async("org_async_test")

        assert org.id == "org_async_test"
        assert org.name == "Async Org"


class TestOrganizationReset:
    """Tests for resetting organizations."""

    def test_reset_clears_organizations(self, mock_clerk: MockClerkClient) -> None:
        """Reset removes all organizations."""

        mock_clerk.organizations.add("org_1", name="Org 1")
        mock_clerk.organizations.add("org_2", name="Org 2")

        mock_clerk.organizations.reset()

        with pytest.raises(ClerkErrors):
            mock_clerk.organizations.get("org_1")

        with pytest.raises(ClerkErrors):
            mock_clerk.organizations.get("org_2")
