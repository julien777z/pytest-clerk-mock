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

