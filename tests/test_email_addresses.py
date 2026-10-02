import pytest
from clerk_backend_api.models import ClerkErrors, CreateEmailAddressRequestBody

from pytest_clerk_mock.client import MockClerkClient


class TestEmailAddresses:
    """Test that email addresses are stored on the users that hold them."""

    async def test_added_address_belongs_to_user(self, mock_clerk: MockClerkClient) -> None:
        """Test that an added address appears on its user and reads back by ID."""

        user = mock_clerk.users.create(email_address=["first@example.test"])

        added = await mock_clerk.email_addresses.create_async(
            request=CreateEmailAddressRequestBody(
                user_id=user.id, email_address="second@example.test", verified=True, primary=True
            )
        )
        stored = mock_clerk.users.get(user_id=user.id)

        assert [email.email_address for email in stored.email_addresses] == [
            "first@example.test",
            "second@example.test",
        ]
        assert stored.primary_email_address_id == added.id
        assert (
            mock_clerk.email_addresses.get(email_address_id=added.id).email_address == "second@example.test"
        )

    async def test_removed_primary_hands_primary_on(self, mock_clerk: MockClerkClient) -> None:
        """Test that removing the primary address promotes the next one and frees the address."""

        user = mock_clerk.users.create(email_address=["first@example.test", "second@example.test"])
        primary = user.primary_email_address_id

        deleted = await mock_clerk.email_addresses.delete_async(email_address_id=primary)
        stored = mock_clerk.users.get(user_id=user.id)
        other = mock_clerk.users.create(email_address=["first@example.test"])

        assert deleted.deleted is True
        assert [email.email_address for email in stored.email_addresses] == ["second@example.test"]
        assert stored.primary_email_address_id == stored.email_addresses[0].id
        assert other.email_addresses[0].email_address == "first@example.test"

    def test_address_held_elsewhere_is_refused(self, mock_clerk: MockClerkClient) -> None:
        """Test that an address another user holds cannot be added."""

        mock_clerk.users.create(email_address=["taken@example.test"])
        second = mock_clerk.users.create(email_address=["own@example.test"])

        with pytest.raises(ClerkErrors):
            mock_clerk.email_addresses.create(
                request={"user_id": second.id, "email_address": "taken@example.test"}
            )

    def test_unknown_address_is_not_found(self, mock_clerk: MockClerkClient) -> None:
        """Test that an unknown address raises Clerk's not-found error."""

        with pytest.raises(ClerkErrors):
            mock_clerk.email_addresses.get(email_address_id="idn_missing")

    def test_replacement_becomes_the_only_primary(self, mock_clerk: MockClerkClient) -> None:
        """Test that replacing a user's address leaves the new one as their primary address."""

        user = mock_clerk.users.create(email_address=["old@example.test"])

        replacement = mock_clerk.email_addresses.replace_for_user(
            user_id=user.id, email_address="new@example.test"
        )
        stored = mock_clerk.users.get(user_id=user.id)

        assert [email.email_address for email in stored.email_addresses] == ["new@example.test"]
        assert stored.primary_email_address_id == replacement.id

    def test_verification_marks_address_verified(self, mock_clerk: MockClerkClient) -> None:
        """Test that a completed verification leaves the address verified."""

        user = mock_clerk.users.create(email_address=["check@example.test"])
        address_id = user.email_addresses[0].id
        mock_clerk.email_addresses.update(email_address_id=address_id, verified=False)

        mock_clerk.email_addresses.prepare_verification(email_address_id=address_id)
        response = mock_clerk.email_addresses.attempt_verification(
            email_address_id=address_id, verification_id="ver_example", code="000000"
        )

        assert response.status == "verified"
        assert (
            mock_clerk.email_addresses.get(email_address_id=address_id).verification["status"] == "verified"
        )
