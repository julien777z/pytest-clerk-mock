from __future__ import annotations

from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Any, Callable, Final, List, Mapping, Tuple

import httpx
from clerk_backend_api import models, utils
from clerk_backend_api._hooks.types import HookContext
from clerk_backend_api.models import ClerkErrors
from clerk_backend_api.types import UNSET, OptionalNullable

from pytest_clerk_mock.services.users import MockUsersClient
from pytest_clerk_mock.utils import (
    build_http_response,
    create_clerk_error,
    generate_clerk_id,
    get_request_value,
)

RESOURCE_NOT_FOUND_ERROR_CODE: Final[str] = "resource_not_found"
SESSION_NOT_FOUND_RESPONSE_TEXT: Final[str] = "Session not found."
SESSION_LIFETIME: Final[timedelta] = timedelta(days=7)
JWT_TEMPLATE: Final[str] = "jwt_{session_id}_{token}"


def _create_session_not_found_error(session_id: str) -> ClerkErrors:
    """Create a ClerkErrors exception for a missing session."""

    return create_clerk_error(
        status_code=HTTPStatus.NOT_FOUND,
        response_text=SESSION_NOT_FOUND_RESPONSE_TEXT,
        code=RESOURCE_NOT_FOUND_ERROR_CODE,
        message=f"Session not found: {session_id}",
    )


def _milliseconds(moment: datetime) -> int:
    """Return a moment as Clerk's millisecond timestamp."""

    return int(moment.timestamp() * 1000)


class MockSessionsClient:
    """Mock implementation of Clerk's Sessions API."""

    def __init__(self, users: MockUsersClient) -> None:
        self._users = users
        self._sessions: dict[str, models.Session] = {}

    def reset(self) -> None:
        """Clear every stored session."""

        self._sessions.clear()

    def _session_or_error(self, session_id: str) -> models.Session:
        """Return a stored session, or raise the Clerk not-found error."""

        if session_id not in self._sessions:
            raise _create_session_not_found_error(session_id)

        return self._sessions[session_id]

    def _issue_jwt(self, session_id: str) -> str:
        """Issue an opaque token string for an active session."""

        session = self._session_or_error(session_id)

        return JWT_TEMPLATE.format(session_id=session.id, token=generate_clerk_id())

    def create(
        self,
        *,
        request: models.CreateSessionRequestBody | models.CreateSessionRequestBodyTypedDict | None = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.Session:
        """Start an active session for a user."""

        _ = retries, server_url, timeout_ms, http_headers

        user_id = get_request_value(request, "user_id")
        self._users._get_user_or_error(user_id)
        started_at = datetime.now()
        session = models.Session.model_validate(
            {
                "object": "session",
                "id": generate_clerk_id("sess"),
                "user_id": user_id,
                "client_id": generate_clerk_id("client"),
                "status": "active",
                "last_active_organization_id": get_request_value(request, "active_organization_id"),
                "last_active_at": _milliseconds(started_at),
                "expire_at": _milliseconds(started_at + SESSION_LIFETIME),
                "abandon_at": _milliseconds(started_at + SESSION_LIFETIME),
                "created_at": _milliseconds(started_at),
                "updated_at": _milliseconds(started_at),
            }
        )
        self._sessions[session.id] = session

        return session

    def get(
        self,
        *,
        session_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.Session:
        """Get a session by ID."""

        _ = retries, server_url, timeout_ms, http_headers

        return self._session_or_error(session_id)

    def list(
        self,
        *,
        client_id: str | None = None,
        user_id: str | None = None,
        status: models.QueryParamStatus | None = None,
        paginated: bool | None = None,
        limit: int | None = 10,
        offset: int | None = 0,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> List[models.Session]:
        """List sessions matching the given filters, newest first."""

        _ = paginated, retries, server_url, timeout_ms, http_headers

        matching = sorted(
            (
                session
                for session in self._sessions.values()
                if (client_id is None or session.client_id == client_id)
                and (user_id is None or session.user_id == user_id)
                and (status is None or session.status.value == status.value)
            ),
            key=lambda session: session.created_at,
            reverse=True,
        )
        start = offset or 0

        return matching[start : start + (limit or 10)]

    def revoke(
        self,
        *,
        session_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.Session:
        """End a session so it can issue no more tokens."""

        _ = retries, server_url, timeout_ms, http_headers

        revoked = self._session_or_error(session_id).model_copy(
            update={"status": models.Status.REVOKED, "updated_at": _milliseconds(datetime.now())}
        )
        self._sessions[session_id] = revoked

        return revoked

    def create_token(
        self,
        *,
        session_id: str,
        expires_in_seconds: OptionalNullable[int] = UNSET,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.CreateSessionTokenResponseBody:
        """Issue a session token."""

        _ = expires_in_seconds, retries, server_url, timeout_ms, http_headers

        return models.CreateSessionTokenResponseBody.model_validate(
            {"object": "token", "jwt": self._issue_jwt(session_id)}
        )

    def create_token_from_template(
        self,
        *,
        session_id: str,
        template_name: str,
        expires_in_seconds: OptionalNullable[int] = UNSET,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.CreateSessionTokenFromTemplateResponseBody:
        """Issue a session token shaped by a JWT template."""

        _ = template_name, expires_in_seconds, retries, server_url, timeout_ms, http_headers

        return models.CreateSessionTokenFromTemplateResponseBody.model_validate(
            {"object": "token", "jwt": self._issue_jwt(session_id)}
        )

    def refresh(
        self,
        *,
        session_id: str,
        expired_token: str,
        refresh_token: str,
        request_origin: str,
        request_headers: OptionalNullable[Mapping[str, Any]] = UNSET,
        format_: OptionalNullable[models.Format] = models.Format.TOKEN,
        request_originating_ip: OptionalNullable[str] = UNSET,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.SessionRefresh:
        """Issue a fresh token for a session."""

        _ = expired_token, refresh_token, request_origin, request_headers, format_, request_originating_ip
        _ = retries, server_url, timeout_ms, http_headers

        return models.Token.model_validate({"object": "token", "jwt": self._issue_jwt(session_id)})

    def do_request(
        self,
        hook_ctx: HookContext,
        request: httpx.Request,
        is_error_status_code: Callable[[int], bool],
        stream: bool = False,
        retry_config: Tuple[utils.RetryConfig, List[str]] | None = None,
    ) -> httpx.Response:
        """Return a generic successful response for low-level SDK hooks."""

        _ = hook_ctx, request, is_error_status_code, stream, retry_config

        return build_http_response()

    async def create_async(
        self,
        *,
        request: models.CreateSessionRequestBody | models.CreateSessionRequestBodyTypedDict | None = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.Session:
        """Async version of create."""

        return self.create(
            request=request,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def get_async(
        self,
        *,
        session_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.Session:
        """Async version of get."""

        return self.get(
            session_id=session_id,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def list_async(
        self,
        *,
        client_id: str | None = None,
        user_id: str | None = None,
        status: models.QueryParamStatus | None = None,
        paginated: bool | None = None,
        limit: int | None = 10,
        offset: int | None = 0,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> List[models.Session]:
        """Async version of list."""

        return self.list(
            client_id=client_id,
            user_id=user_id,
            status=status,
            paginated=paginated,
            limit=limit,
            offset=offset,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def revoke_async(
        self,
        *,
        session_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.Session:
        """Async version of revoke."""

        return self.revoke(
            session_id=session_id,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def create_token_async(
        self,
        *,
        session_id: str,
        expires_in_seconds: OptionalNullable[int] = UNSET,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.CreateSessionTokenResponseBody:
        """Async version of create_token."""

        return self.create_token(
            session_id=session_id,
            expires_in_seconds=expires_in_seconds,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def create_token_from_template_async(
        self,
        *,
        session_id: str,
        template_name: str,
        expires_in_seconds: OptionalNullable[int] = UNSET,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.CreateSessionTokenFromTemplateResponseBody:
        """Async version of create_token_from_template."""

        return self.create_token_from_template(
            session_id=session_id,
            template_name=template_name,
            expires_in_seconds=expires_in_seconds,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def refresh_async(
        self,
        *,
        session_id: str,
        expired_token: str,
        refresh_token: str,
        request_origin: str,
        request_headers: OptionalNullable[Mapping[str, Any]] = UNSET,
        format_: OptionalNullable[models.Format] = models.Format.TOKEN,
        request_originating_ip: OptionalNullable[str] = UNSET,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.SessionRefresh:
        """Async version of refresh."""

        return self.refresh(
            session_id=session_id,
            expired_token=expired_token,
            refresh_token=refresh_token,
            request_origin=request_origin,
            request_headers=request_headers,
            format_=format_,
            request_originating_ip=request_originating_ip,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def do_request_async(
        self,
        hook_ctx: HookContext,
        request: httpx.Request,
        is_error_status_code: Callable[[int], bool],
        stream: bool = False,
        retry_config: Tuple[utils.RetryConfig, List[str]] | None = None,
    ) -> httpx.Response:
        """Async version of do_request."""

        return self.do_request(
            hook_ctx,
            request,
            is_error_status_code,
            stream=stream,
            retry_config=retry_config,
        )
