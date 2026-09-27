import pytest
from clerk_backend_api.models import ClerkErrors, CreateSessionRequestBody, QueryParamStatus, Status

from pytest_clerk_mock.client import MockClerkClient


class TestSessions:
    """Test that sessions start, issue tokens and end."""

    async def test_session_issues_tokens(self, mock_clerk: MockClerkClient) -> None:
        """Test that a started session is active and issues a token naming it."""

        user = mock_clerk.users.create(email_address=["session@example.test"])

        session = await mock_clerk.sessions.create_async(request=CreateSessionRequestBody(user_id=user.id))
        token = await mock_clerk.sessions.create_token_async(session_id=session.id)
        templated = mock_clerk.sessions.create_token_from_template(
            session_id=session.id, template_name="example"
        )

        assert session.status is Status.ACTIVE
        assert session.user_id == user.id
        assert token.jwt is not None and session.id in token.jwt
        assert templated.jwt is not None and templated.jwt != token.jwt

    def test_list_filters_by_user_and_status(self, mock_clerk: MockClerkClient) -> None:
        """Test that listing returns only the sessions matching every filter given."""

        first = mock_clerk.users.create(email_address=["first@example.test"])
        second = mock_clerk.users.create(email_address=["second@example.test"])
        kept = mock_clerk.sessions.create(request={"user_id": first.id})
        ended = mock_clerk.sessions.create(request={"user_id": first.id})
        mock_clerk.sessions.create(request={"user_id": second.id})

        mock_clerk.sessions.revoke(session_id=ended.id)
        active = mock_clerk.sessions.list(user_id=first.id, status=QueryParamStatus.ACTIVE)

        assert [session.id for session in active] == [kept.id]

    async def test_revoked_session_reads_back_revoked(self, mock_clerk: MockClerkClient) -> None:
        """Test that a revoked session reads back as revoked."""

        user = mock_clerk.users.create(email_address=["session@example.test"])
        session = mock_clerk.sessions.create(request={"user_id": user.id})

        await mock_clerk.sessions.revoke_async(session_id=session.id)

        assert mock_clerk.sessions.get(session_id=session.id).status is Status.REVOKED

    def test_unknown_session_is_not_found(self, mock_clerk: MockClerkClient) -> None:
        """Test that a token for an unknown session raises Clerk's not-found error."""

        with pytest.raises(ClerkErrors):
            mock_clerk.sessions.create_token(session_id="sess_missing")

    def test_refresh_issues_a_new_token(self, mock_clerk: MockClerkClient) -> None:
        """Test that refreshing a session returns a fresh token."""

        user = mock_clerk.users.create(email_address=["session@example.test"])
        session = mock_clerk.sessions.create(request={"user_id": user.id})

        refreshed = mock_clerk.sessions.refresh(
            session_id=session.id,
            expired_token="expired",
            refresh_token="refresh",
            request_origin="https://app.example.test",
        )

        assert session.id in refreshed.jwt
