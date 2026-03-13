import pytest
from clerk_backend_api.models import ClerkErrors, GetUserListRequest

from pytest_clerk_mock import (
    MockAuthResult,
    MockClerkClient,
    MockClerkUser,
    mock_clerk_backend,
)


class TestAuthenticateRequest:
    """Tests for authenticate_request method."""

    def test_default_user_is_authenticated(self, mock_clerk: MockClerkClient) -> None:
        """Default configuration returns authenticated user."""

        result = mock_clerk.authenticate_request(request=None)

        assert result.is_signed_in is True
        assert result.payload["sub"] == "user_test_owner"
        assert result.payload["org_id"] == "org_test_123"
        assert result.payload["org_role"] == "org:admin"

    def test_configure_auth_changes_result(self, mock_clerk: MockClerkClient) -> None:
        """configure_auth updates the authentication state."""

        mock_clerk.configure_auth("user_custom", "org_custom", "org:member")

        result = mock_clerk.authenticate_request(request=None)

        assert result.is_signed_in is True
        assert result.payload["sub"] == "user_custom"
        assert result.payload["org_id"] == "org_custom"
        assert result.payload["org_role"] == "org:member"

    def test_configure_auth_unauthenticated(self, mock_clerk: MockClerkClient) -> None:
        """Setting user_id to None makes user unauthenticated."""

        mock_clerk.configure_auth(None)

        result = mock_clerk.authenticate_request(request=None)

        assert result.is_signed_in is False
        assert result.payload == {}

    def test_configure_auth_from_user_enum(self, mock_clerk: MockClerkClient) -> None:
        """configure_auth_from_user accepts MockClerkUser enum."""

        mock_clerk.configure_auth_from_user(MockClerkUser.TEAM_MEMBER, "org_456")

        result = mock_clerk.authenticate_request(request=None)

        assert result.is_signed_in is True
        assert result.payload["sub"] == "user_test_member"
        assert result.payload["org_id"] == "org_456"

    def test_configure_auth_from_user_unauthenticated(self, mock_clerk: MockClerkClient) -> None:
        """MockClerkUser.UNAUTHENTICATED sets user as not signed in."""

        mock_clerk.configure_auth_from_user(MockClerkUser.UNAUTHENTICATED)

        result = mock_clerk.authenticate_request(request=None)

        assert result.is_signed_in is False


class TestAsUserContextManager:
    """Tests for as_user context manager."""

    def test_as_user_temporarily_changes_auth(self, mock_clerk: MockClerkClient) -> None:
        """as_user temporarily switches the authenticated user."""

        original_result = mock_clerk.authenticate_request(request=None)
        assert original_result.payload["sub"] == "user_test_owner"

        with mock_clerk.as_user("user_temp", "org_temp"):
            temp_result = mock_clerk.authenticate_request(request=None)
            assert temp_result.payload["sub"] == "user_temp"
            assert temp_result.payload["org_id"] == "org_temp"

        restored_result = mock_clerk.authenticate_request(request=None)
        assert restored_result.payload["sub"] == "user_test_owner"

    def test_as_user_restores_on_exception(self, mock_clerk: MockClerkClient) -> None:
        """as_user restores state even when exception is raised."""

        original_result = mock_clerk.authenticate_request(request=None)
        original_user = original_result.payload["sub"]

        with pytest.raises(ValueError):
            with mock_clerk.as_user("user_temp"):
                raise ValueError("Test exception")

        restored_result = mock_clerk.authenticate_request(request=None)
        assert restored_result.payload["sub"] == original_user

    def test_as_user_unauthenticated(self, mock_clerk: MockClerkClient) -> None:
        """as_user with None user_id simulates unauthenticated."""

        with mock_clerk.as_user(None):
            result = mock_clerk.authenticate_request(request=None)
            assert result.is_signed_in is False

    def test_as_clerk_user_with_enum(self, mock_clerk: MockClerkClient) -> None:
        """as_clerk_user accepts MockClerkUser enum."""

        with mock_clerk.as_clerk_user(MockClerkUser.GUEST, "org_123"):
            result = mock_clerk.authenticate_request(request=None)
            assert result.payload["sub"] == "user_test_guest"
            assert result.payload["org_id"] == "org_123"


class TestOrganizationMemberships:
    """Tests for organization membership functionality."""

    def test_add_organization_membership(self, mock_clerk: MockClerkClient) -> None:
        """add_organization_membership creates a membership."""

        membership = mock_clerk.add_organization_membership(
            user_id="user_123",
            org_id="org_456",
            role="org:admin",
            org_name="Test Org",
        )

        assert membership.id.startswith("orgmem_")
        assert membership.role == "org:admin"
        assert membership.organization is not None
        assert membership.organization.id == "org_456"
        assert membership.organization.name == "Test Org"

    async def test_get_organization_memberships_async(self, mock_clerk: MockClerkClient) -> None:
        """get_organization_memberships_async returns configured memberships."""

        mock_clerk.add_organization_membership(
            user_id="user_123",
            org_id="org_456",
            role="org:admin",
        )
        mock_clerk.add_organization_membership(
            user_id="user_123",
            org_id="org_789",
            role="org:member",
        )

        memberships = await mock_clerk._get_organization_memberships_async("user_123")

        assert len(memberships.data) == 2
        assert memberships.data[0].organization.id == "org_456"
        assert memberships.data[1].organization.id == "org_789"

    async def test_get_organization_memberships_empty(self, mock_clerk: MockClerkClient) -> None:
        """get_organization_memberships_async returns empty for unknown user."""

        memberships = await mock_clerk._get_organization_memberships_async("user_unknown")

        assert len(memberships.data) == 0
        assert memberships.total_count == 0


class TestMockClerkBackendContextManager:
    """Tests for mock_clerk_backend context manager."""

    def test_mock_clerk_backend_default(self) -> None:
        """mock_clerk_backend works with defaults."""

        with mock_clerk_backend() as client:
            result = client.authenticate_request(request=None)

            assert result.is_signed_in is True
            assert result.payload["sub"] == "user_test_owner"

    def test_mock_clerk_backend_custom_defaults(self) -> None:
        """mock_clerk_backend accepts custom default configuration."""

        with mock_clerk_backend(
            default_user_id="custom_user",
            default_org_id="custom_org",
            default_org_role="org:custom",
        ) as client:
            result = client.authenticate_request(request=None)

            assert result.payload["sub"] == "custom_user"
            assert result.payload["org_id"] == "custom_org"
            assert result.payload["org_role"] == "org:custom"

    def test_mock_clerk_backend_unauthenticated_default(self) -> None:
        """mock_clerk_backend can default to unauthenticated."""

        with mock_clerk_backend(default_user_id=None) as client:
            result = client.authenticate_request(request=None)

            assert result.is_signed_in is False


class TestMockAuthResult:
    """Tests for MockAuthResult model."""

    def test_signed_in_factory(self) -> None:
        """signed_in creates authenticated result."""

        result = MockAuthResult.signed_in(
            user_id="user_123",
            org_id="org_456",
            org_role="org:admin",
        )

        assert result.is_signed_in is True
        assert result.payload["sub"] == "user_123"
        assert result.payload["org_id"] == "org_456"
        assert result.payload["org_role"] == "org:admin"

    def test_signed_out_factory(self) -> None:
        """signed_out creates unauthenticated result."""

        result = MockAuthResult.signed_out()

        assert result.is_signed_in is False
        assert result.payload == {}


class TestMockClerkUserEnum:
    """Tests for MockClerkUser enum."""

    def test_team_owner_value(self) -> None:
        """TEAM_OWNER has expected value."""

        assert MockClerkUser.TEAM_OWNER.value == "user_test_owner"

    def test_team_member_value(self) -> None:
        """TEAM_MEMBER has expected value."""

        assert MockClerkUser.TEAM_MEMBER.value == "user_test_member"

    def test_guest_value(self) -> None:
        """GUEST has expected value."""

        assert MockClerkUser.GUEST.value == "user_test_guest"

    def test_unauthenticated_value(self) -> None:
        """UNAUTHENTICATED has None value."""

        assert MockClerkUser.UNAUTHENTICATED.value is None


class TestClerkErrorsOnDuplicateEmail:
    """Tests for ClerkErrors exception on duplicate email."""

    def test_duplicate_email_raises_clerk_errors(self, mock_clerk: MockClerkClient) -> None:
        """Duplicate email raises ClerkErrors by default."""

        mock_clerk.users.create(email_address=["test@example.com"])

        with pytest.raises(ClerkErrors) as exc_info:
            mock_clerk.users.create(email_address=["test@example.com"])

        errors = exc_info.value.data.errors
        assert len(errors) == 1
        assert errors[0].code == "form_identifier_exists"

    async def test_duplicate_email_raises_clerk_errors_async(self, mock_clerk: MockClerkClient) -> None:
        """Async create also raises ClerkErrors for duplicate email."""

        await mock_clerk.users.create_async(email_address=["test@example.com"])

        with pytest.raises(ClerkErrors):
            await mock_clerk.users.create_async(email_address=["test@example.com"])


class TestListAsyncResponse:
    """Tests for list_async response."""

    async def test_list_async_returns_list(self, mock_clerk: MockClerkClient) -> None:
        """list_async returns a list of users."""

        await mock_clerk.users.create_async(email_address=["user1@example.com"])
        await mock_clerk.users.create_async(email_address=["user2@example.com"])

        response = await mock_clerk.users.list_async()

        assert isinstance(response, list)
        assert len(response) == 2
        assert response[0].email_addresses[0].email_address in [
            "user1@example.com",
            "user2@example.com",
        ]

    async def test_list_async_filter_by_email(self, mock_clerk: MockClerkClient) -> None:
        """list_async with email filter returns filtered list."""

        await mock_clerk.users.create_async(email_address=["target@example.com"])
        await mock_clerk.users.create_async(email_address=["other@example.com"])

        request = GetUserListRequest(email_address=["target@example.com"])
        response = await mock_clerk.users.list_async(request=request)

        assert len(response) == 1
        assert response[0].email_addresses[0].email_address == "target@example.com"

    async def test_list_async_empty_response(self, mock_clerk: MockClerkClient) -> None:
        """list_async returns empty list for no results."""

        response = await mock_clerk.users.list_async()

        assert response == []


class TestClientReset:
    """Tests for client reset functionality."""

    def test_reset_clears_auth_state(self, mock_clerk: MockClerkClient) -> None:
        """reset() clears authentication configuration."""

        mock_clerk.configure_auth("custom_user", "custom_org")
        mock_clerk.reset()

        result = mock_clerk.authenticate_request(request=None)

        assert result.is_signed_in is False

    def test_reset_clears_users(self, mock_clerk: MockClerkClient) -> None:
        """reset() clears all users."""

        mock_clerk.users.create(email_address=["test@example.com"])
        mock_clerk.reset()

        users = mock_clerk.users.list()

        assert len(users) == 0

    def test_reset_clears_memberships(self, mock_clerk: MockClerkClient) -> None:
        """reset() clears all organization memberships."""

        mock_clerk.add_organization_membership("user_123", "org_456")
        mock_clerk.reset()

        # Memberships are stored on client, not visible via users
        # This ensures the internal state is cleared
        assert mock_clerk._memberships == {}
