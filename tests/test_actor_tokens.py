import pytest
from clerk_backend_api.models import ActorTokenStatus, ClerkErrors

from pytest_clerk_mock.client import MockClerkClient


class TestActorTokens:
    """Test that actor tokens let one user act as another until revoked."""

    async def test_token_is_issued_pending(self, mock_clerk: MockClerkClient) -> None:
        """Test that a new token is pending, names its subject and carries a sign-in URL."""

        subject = mock_clerk.users.create(email_address=["subject@example.test"])

        issued = await mock_clerk.actor_tokens.create_async(
            request={"user_id": subject.id, "actor": {"sub": "user_actor_example"}}
        )

        assert issued.status is ActorTokenStatus.PENDING
        assert issued.user_id == subject.id
        assert issued.token is not None
        assert issued.url is not None and issued.token in issued.url

    async def test_revoked_token_reports_revoked(self, mock_clerk: MockClerkClient) -> None:
        """Test that revoking a token marks it revoked."""

        subject = mock_clerk.users.create(email_address=["subject@example.test"])
        issued = mock_clerk.actor_tokens.create(
            request={"user_id": subject.id, "actor": {"sub": "user_actor"}}
        )

        revoked = await mock_clerk.actor_tokens.revoke_async(actor_token_id=issued.id)

        assert revoked.status is ActorTokenStatus.REVOKED

    def test_unknown_subject_is_refused(self, mock_clerk: MockClerkClient) -> None:
        """Test that a token for a user the mock does not hold raises Clerk's not-found error."""

        with pytest.raises(ClerkErrors):
            mock_clerk.actor_tokens.create(
                request={"user_id": "user_missing", "actor": {"sub": "user_actor"}}
            )

    def test_reset_forgets_tokens(self, mock_clerk: MockClerkClient) -> None:
        """Test that a reset client cannot revoke a token issued before it."""

        subject = mock_clerk.users.create(email_address=["subject@example.test"])
        issued = mock_clerk.actor_tokens.create(
            request={"user_id": subject.id, "actor": {"sub": "user_actor"}}
        )

        mock_clerk.actor_tokens.reset()

        with pytest.raises(ClerkErrors):
            mock_clerk.actor_tokens.revoke(actor_token_id=issued.id)
