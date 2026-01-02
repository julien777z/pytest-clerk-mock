import pytest
from clerk_backend_api.models import ClerkErrors, GetUserListRequest

from pytest_clerk_mock.client import MockClerkClient
from pytest_clerk_mock.services.users import UserNotFoundError


class TestUserCreate:
    """Tests for user creation."""

    def test_create_user_with_email(self, mock_clerk: MockClerkClient) -> None:
        """Create a user with email sets primary email."""

        user = mock_clerk.users.create(
            email_address=["test@example.com"],
            first_name="John",
            last_name="Doe",
        )

        assert user.id.startswith("user_")
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert len(user.email_addresses) == 1
        assert user.email_addresses[0].email_address == "test@example.com"
        assert user.primary_email_address_id == user.email_addresses[0].id

    def test_create_user_with_multiple_emails(self, mock_clerk: MockClerkClient) -> None:
        """First email becomes primary when multiple provided."""

        user = mock_clerk.users.create(
            email_address=["primary@example.com", "secondary@example.com"],
        )

        assert len(user.email_addresses) == 2
        assert user.primary_email_address_id == user.email_addresses[0].id

    def test_create_user_with_phone(self, mock_clerk: MockClerkClient) -> None:
        """Create a user with phone sets primary phone."""

        user = mock_clerk.users.create(
            phone_number=["+15551234567"],
        )

        assert len(user.phone_numbers) == 1
        assert user.phone_numbers[0].phone_number == "+15551234567"
        assert user.primary_phone_number_id == user.phone_numbers[0].id

    def test_create_user_with_username(self, mock_clerk: MockClerkClient) -> None:
        """Create a user with username."""

        user = mock_clerk.users.create(
            username="johndoe",
            first_name="John",
        )

        assert user.username == "johndoe"

    def test_create_user_with_password(self, mock_clerk: MockClerkClient) -> None:
        """Password sets password_enabled to True."""

        user = mock_clerk.users.create(
            email_address=["test@example.com"],
            password="secretpassword123",
        )

        assert user.password_enabled is True

    def test_create_user_with_metadata(self, mock_clerk: MockClerkClient) -> None:
        """Create a user with all metadata types."""

        user = mock_clerk.users.create(
            email_address=["test@example.com"],
            public_metadata={"role": "admin"},
            private_metadata={"internal_id": "123"},
            unsafe_metadata={"preferences": {"theme": "dark"}},
        )

        assert user.public_metadata == {"role": "admin"}
        assert user.private_metadata == {"internal_id": "123"}
        assert user.unsafe_metadata == {"preferences": {"theme": "dark"}}

    def test_create_user_with_external_id(self, mock_clerk: MockClerkClient) -> None:
        """Create a user with external ID."""

        user = mock_clerk.users.create(
            email_address=["test@example.com"],
            external_id="ext_123",
        )

        assert user.external_id == "ext_123"

    def test_create_user_duplicate_email_raises(self, mock_clerk: MockClerkClient) -> None:
        """Duplicate email raises ClerkErrors with form_identifier_exists code."""

        mock_clerk.users.create(email_address=["test@example.com"])

        with pytest.raises(ClerkErrors) as exc_info:
            mock_clerk.users.create(email_address=["test@example.com"])

        errors = exc_info.value.data.errors
        assert len(errors) == 1
        assert errors[0].code == "form_identifier_exists"

    def test_create_user_duplicate_email_case_insensitive(
        self, mock_clerk: MockClerkClient
    ) -> None:
        """Email uniqueness check is case insensitive."""

        mock_clerk.users.create(email_address=["test@example.com"])

        with pytest.raises(ClerkErrors):
            mock_clerk.users.create(email_address=["TEST@EXAMPLE.COM"])


class TestUserGet:
    """Tests for getting users by ID."""

    def test_get_user(self, mock_clerk: MockClerkClient) -> None:
        """Get user returns the created user."""

        created = mock_clerk.users.create(
            email_address=["test@example.com"],
            first_name="John",
        )

        fetched = mock_clerk.users.get(created.id)

        assert fetched.id == created.id
        assert fetched.first_name == "John"
        assert fetched.email_addresses[0].email_address == "test@example.com"

    def test_get_user_not_found(self, mock_clerk: MockClerkClient) -> None:
        """Nonexistent user raises UserNotFoundError."""

        with pytest.raises(UserNotFoundError) as exc_info:
            mock_clerk.users.get("user_nonexistent")

        assert exc_info.value.user_id == "user_nonexistent"


class TestUserList:
    """Tests for listing users with filters."""

    def test_list_empty(self, mock_clerk: MockClerkClient) -> None:
        """Empty store returns empty list."""

        users = mock_clerk.users.list()

        assert users == []

    def test_list_all_users(self, mock_clerk: MockClerkClient) -> None:
        """List without filters returns all users."""

        mock_clerk.users.create(email_address=["user1@example.com"])
        mock_clerk.users.create(email_address=["user2@example.com"])
        mock_clerk.users.create(email_address=["user3@example.com"])

        users = mock_clerk.users.list()

        assert len(users) == 3

    def test_list_filter_by_email(self, mock_clerk: MockClerkClient) -> None:
        """Filter by email returns matching users."""

        mock_clerk.users.create(email_address=["user1@example.com"])
        user2 = mock_clerk.users.create(email_address=["user2@example.com"])
        mock_clerk.users.create(email_address=["user3@example.com"])

        users = mock_clerk.users.list(email_address=["user2@example.com"])

        assert len(users) == 1
        assert users[0].id == user2.id

    def test_list_filter_by_external_id(self, mock_clerk: MockClerkClient) -> None:
        """Filter by external_id returns matching users."""

        mock_clerk.users.create(email_address=["user1@example.com"], external_id="ext_1")
        user2 = mock_clerk.users.create(
            email_address=["user2@example.com"], external_id="ext_2"
        )

        users = mock_clerk.users.list(external_id=["ext_2"])

        assert len(users) == 1
        assert users[0].id == user2.id

    def test_list_filter_by_username(self, mock_clerk: MockClerkClient) -> None:
        """Filter by username returns matching users."""

        mock_clerk.users.create(username="alice")
        bob = mock_clerk.users.create(username="bob")

        users = mock_clerk.users.list(username=["bob"])

        assert len(users) == 1
        assert users[0].id == bob.id

    def test_list_filter_by_query(self, mock_clerk: MockClerkClient) -> None:
        """Query searches name and email fields."""

        mock_clerk.users.create(email_address=["alice@example.com"], first_name="Alice")
        bob = mock_clerk.users.create(email_address=["bob@example.com"], first_name="Bob")

        users = mock_clerk.users.list(query="bob")

        assert len(users) == 1
        assert users[0].id == bob.id

    def test_list_with_limit(self, mock_clerk: MockClerkClient) -> None:
        """Limit restricts number of returned users."""

        for i in range(5):
            mock_clerk.users.create(email_address=[f"user{i}@example.com"])

        users = mock_clerk.users.list(limit=2)

        assert len(users) == 2

    def test_list_with_offset(self, mock_clerk: MockClerkClient) -> None:
        """Offset skips the first N users."""

        for i in range(5):
            mock_clerk.users.create(email_address=[f"user{i}@example.com"])

        users = mock_clerk.users.list(limit=10, offset=3)

        assert len(users) == 2


class TestUserUpdate:
    """Tests for updating users."""

    def test_update_first_name(self, mock_clerk: MockClerkClient) -> None:
        """Update persists first_name change."""

        user = mock_clerk.users.create(
            email_address=["test@example.com"],
            first_name="John",
        )

        updated = mock_clerk.users.update(user.id, first_name="Jane")

        assert updated.first_name == "Jane"
        assert mock_clerk.users.get(user.id).first_name == "Jane"

    def test_update_multiple_fields(self, mock_clerk: MockClerkClient) -> None:
        """Multiple fields can be updated at once."""

        user = mock_clerk.users.create(
            email_address=["test@example.com"],
            first_name="John",
            last_name="Doe",
        )

        updated = mock_clerk.users.update(
            user.id,
            first_name="Jane",
            last_name="Smith",
            username="janesmith",
        )

        assert updated.first_name == "Jane"
        assert updated.last_name == "Smith"
        assert updated.username == "janesmith"

    def test_update_metadata(self, mock_clerk: MockClerkClient) -> None:
        """Metadata can be updated."""

        user = mock_clerk.users.create(
            email_address=["test@example.com"],
            public_metadata={"role": "user"},
        )

        updated = mock_clerk.users.update(
            user.id,
            public_metadata={"role": "admin"},
        )

        assert updated.public_metadata == {"role": "admin"}

    def test_update_user_not_found(self, mock_clerk: MockClerkClient) -> None:
        """Update nonexistent user raises UserNotFoundError."""

        with pytest.raises(UserNotFoundError):
            mock_clerk.users.update("user_nonexistent", first_name="Test")


class TestUserDelete:
    """Tests for deleting users."""

    def test_delete_user(self, mock_clerk: MockClerkClient) -> None:
        """Delete removes user from store."""

        user = mock_clerk.users.create(email_address=["test@example.com"])

        deleted = mock_clerk.users.delete(user.id)

        assert deleted.id == user.id

        with pytest.raises(UserNotFoundError):
            mock_clerk.users.get(user.id)

    def test_delete_user_clears_email(self, mock_clerk: MockClerkClient) -> None:
        """Delete frees email for reuse."""

        user = mock_clerk.users.create(email_address=["test@example.com"])
        mock_clerk.users.delete(user.id)

        new_user = mock_clerk.users.create(email_address=["test@example.com"])

        assert new_user.id != user.id

    def test_delete_user_not_found(self, mock_clerk: MockClerkClient) -> None:
        """Delete nonexistent user raises UserNotFoundError."""

        with pytest.raises(UserNotFoundError):
            mock_clerk.users.delete("user_nonexistent")


class TestUserCount:
    """Tests for counting users."""

    def test_count_all(self, mock_clerk: MockClerkClient) -> None:
        """Count returns total number of users."""

        for i in range(5):
            mock_clerk.users.create(email_address=[f"user{i}@example.com"])

        count = mock_clerk.users.count()

        assert count == 5

    def test_count_with_filter(self, mock_clerk: MockClerkClient) -> None:
        """Count respects filters."""

        mock_clerk.users.create(email_address=["user1@example.com"], external_id="ext_1")
        mock_clerk.users.create(email_address=["user2@example.com"], external_id="ext_1")
        mock_clerk.users.create(email_address=["user3@example.com"], external_id="ext_2")

        count = mock_clerk.users.count(external_id=["ext_1"])

        assert count == 2


class TestFixtureIsolation:
    """Tests that fixture resets between tests."""

    def test_fixture_isolation_first(self, mock_clerk: MockClerkClient) -> None:
        """First test creates a user."""

        mock_clerk.users.create(email_address=["isolation@example.com"])
        users = mock_clerk.users.list()

        assert len(users) == 1

    def test_fixture_isolation_second(self, mock_clerk: MockClerkClient) -> None:
        """Second test sees empty store."""

        users = mock_clerk.users.list()

        assert len(users) == 0


class TestAsyncAPI:
    """Tests for async API methods."""

    async def test_create_async(self, mock_clerk: MockClerkClient) -> None:
        """Async create works like sync version."""

        user = await mock_clerk.users.create_async(
            email_address=["async@example.com"],
            first_name="Async",
            last_name="User",
        )

        assert user.id.startswith("user_")
        assert user.first_name == "Async"
        assert user.email_addresses[0].email_address == "async@example.com"

    async def test_get_async(self, mock_clerk: MockClerkClient) -> None:
        """Async get returns created user."""

        created = await mock_clerk.users.create_async(
            email_address=["test@example.com"],
            first_name="John",
        )

        fetched = await mock_clerk.users.get_async(user_id=created.id)

        assert fetched.id == created.id
        assert fetched.first_name == "John"

    async def test_get_async_not_found(self, mock_clerk: MockClerkClient) -> None:
        """Async get raises for nonexistent user."""

        with pytest.raises(UserNotFoundError):
            await mock_clerk.users.get_async(user_id="user_nonexistent")

    async def test_list_async(self, mock_clerk: MockClerkClient) -> None:
        """Async list returns a list of users."""

        await mock_clerk.users.create_async(email_address=["user1@example.com"])
        await mock_clerk.users.create_async(email_address=["user2@example.com"])

        response = await mock_clerk.users.list_async()

        assert len(response) == 2

    async def test_list_async_with_filter(self, mock_clerk: MockClerkClient) -> None:
        """Async list respects filters via request object."""

        await mock_clerk.users.create_async(email_address=["user1@example.com"])
        user2 = await mock_clerk.users.create_async(email_address=["user2@example.com"])

        request = GetUserListRequest(email_address=["user2@example.com"])
        response = await mock_clerk.users.list_async(request=request)

        assert len(response) == 1
        assert response[0].id == user2.id

    async def test_update_async(self, mock_clerk: MockClerkClient) -> None:
        """Async update persists changes."""

        user = await mock_clerk.users.create_async(
            email_address=["test@example.com"],
            first_name="John",
        )

        updated = await mock_clerk.users.update_async(user_id=user.id, first_name="Jane")

        assert updated.first_name == "Jane"

    async def test_update_async_not_found(self, mock_clerk: MockClerkClient) -> None:
        """Async update raises for nonexistent user."""

        with pytest.raises(UserNotFoundError):
            await mock_clerk.users.update_async(user_id="user_nonexistent", first_name="Test")

    async def test_delete_async(self, mock_clerk: MockClerkClient) -> None:
        """Async delete removes user."""

        user = await mock_clerk.users.create_async(email_address=["test@example.com"])

        deleted = await mock_clerk.users.delete_async(user_id=user.id)

        assert deleted.id == user.id

        with pytest.raises(UserNotFoundError):
            await mock_clerk.users.get_async(user_id=user.id)

    async def test_delete_async_not_found(self, mock_clerk: MockClerkClient) -> None:
        """Async delete raises for nonexistent user."""

        with pytest.raises(UserNotFoundError):
            await mock_clerk.users.delete_async(user_id="user_nonexistent")

    async def test_count_async(self, mock_clerk: MockClerkClient) -> None:
        """Async count returns total."""

        for i in range(3):
            await mock_clerk.users.create_async(email_address=[f"user{i}@example.com"])

        count = await mock_clerk.users.count_async()

        assert count == 3

    async def test_count_async_with_filter(self, mock_clerk: MockClerkClient) -> None:
        """Async count respects filters."""

        await mock_clerk.users.create_async(
            email_address=["user1@example.com"], external_id="ext_1"
        )
        await mock_clerk.users.create_async(
            email_address=["user2@example.com"], external_id="ext_2"
        )

        count = await mock_clerk.users.count_async(external_id=["ext_1"])

        assert count == 1

