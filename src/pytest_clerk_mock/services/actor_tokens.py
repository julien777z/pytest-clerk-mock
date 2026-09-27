from __future__ import annotations

from datetime import datetime
from http import HTTPStatus
from typing import Callable, Final, List, Mapping, Tuple

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
ACTOR_TOKEN_NOT_FOUND_RESPONSE_TEXT: Final[str] = "Actor token not found."
SIGN_IN_TICKET_URL: Final[str] = "https://accounts.example.test/sign-in?__clerk_ticket={token}"


def _create_actor_token_not_found_error(actor_token_id: str) -> ClerkErrors:
    """Create a ClerkErrors exception for a missing actor token."""

    return create_clerk_error(
        status_code=HTTPStatus.NOT_FOUND,
        response_text=ACTOR_TOKEN_NOT_FOUND_RESPONSE_TEXT,
        code=RESOURCE_NOT_FOUND_ERROR_CODE,
        message=f"Actor token not found: {actor_token_id}",
    )


def _now_milliseconds() -> int:
    """Return the current time as Clerk's millisecond timestamp."""

    return int(datetime.now().timestamp() * 1000)


class MockActorTokensClient:
    """Mock implementation of Clerk's ActorTokens API."""

    def __init__(self, users: MockUsersClient) -> None:
        self._users = users
        self._tokens: dict[str, models.ActorToken] = {}

    def reset(self) -> None:
        """Clear every issued actor token."""

        self._tokens.clear()

    def create(
        self,
        *,
        request: (
            models.CreateActorTokenRequestBody | models.CreateActorTokenRequestBodyTypedDict | None
        ) = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.ActorToken:
        """Issue a pending actor token letting one user act as another."""

        _ = retries, server_url, timeout_ms, http_headers

        user_id = get_request_value(request, "user_id")
        self._users._get_user_or_error(user_id)
        token = generate_clerk_id("act_tkn")
        issued_at = _now_milliseconds()
        actor_token = models.ActorToken.model_validate(
            {
                "object": "actor_token",
                "id": generate_clerk_id("act"),
                "status": "pending",
                "user_id": user_id,
                "actor": get_request_value(request, "actor"),
                "token": token,
                "url": SIGN_IN_TICKET_URL.format(token=token),
                "created_at": issued_at,
                "updated_at": issued_at,
            }
        )
        self._tokens[actor_token.id] = actor_token

        return actor_token

    def revoke(
        self,
        *,
        actor_token_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.ActorToken:
        """Revoke an actor token so it can no longer be used."""

        _ = retries, server_url, timeout_ms, http_headers

        if actor_token_id not in self._tokens:
            raise _create_actor_token_not_found_error(actor_token_id)

        revoked = self._tokens[actor_token_id].model_copy(
            update={"status": models.ActorTokenStatus.REVOKED, "updated_at": _now_milliseconds()}
        )
        self._tokens[actor_token_id] = revoked

        return revoked

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
        request: (
            models.CreateActorTokenRequestBody | models.CreateActorTokenRequestBodyTypedDict | None
        ) = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.ActorToken:
        """Async version of create."""

        return self.create(
            request=request,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def revoke_async(
        self,
        *,
        actor_token_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.ActorToken:
        """Async version of revoke."""

        return self.revoke(
            actor_token_id=actor_token_id,
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
