from __future__ import annotations

from http import HTTPStatus
from typing import Callable, Final, List, Mapping, Tuple

import httpx
from clerk_backend_api import models, utils
from clerk_backend_api._hooks.types import HookContext
from clerk_backend_api.models import ClerkErrors
from clerk_backend_api.models.replaceuseremailaddressop import IdentificationStatus
from clerk_backend_api.types import UNSET, OptionalNullable

from pytest_clerk_mock.models.user import MockEmailAddress, MockUser
from pytest_clerk_mock.services.users import MockUsersClient
from pytest_clerk_mock.utils import (
    build_http_response,
    create_clerk_error,
    generate_clerk_id,
    get_request_value,
    resolve_optional_nullable,
)

RESOURCE_NOT_FOUND_ERROR_CODE: Final[str] = "resource_not_found"
EMAIL_EXISTS_ERROR_CODE: Final[str] = "form_identifier_exists"
EMAIL_NOT_FOUND_RESPONSE_TEXT: Final[str] = "Email address not found."
EMAIL_EXISTS_RESPONSE_TEXT: Final[str] = "That email address is taken."
VERIFIED_STATUS: Final[str] = "verified"


def _create_email_not_found_error(email_address_id: str) -> ClerkErrors:
    """Create a ClerkErrors exception for a missing email address."""

    return create_clerk_error(
        status_code=HTTPStatus.NOT_FOUND,
        response_text=EMAIL_NOT_FOUND_RESPONSE_TEXT,
        code=RESOURCE_NOT_FOUND_ERROR_CODE,
        message=f"Email address not found: {email_address_id}",
    )


def _create_email_exists_error(email: str) -> ClerkErrors:
    """Create a ClerkErrors exception for an email address another user holds."""

    return create_clerk_error(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        response_text=EMAIL_EXISTS_RESPONSE_TEXT,
        code=EMAIL_EXISTS_ERROR_CODE,
        message=f"That email address is taken: {email}",
    )


def _build_verification_response(status: str) -> models.VerificationResponse:
    """Build a verification payload in the given status."""

    return models.VerificationResponse.model_validate(
        {"object": "verification", "status": status, "strategy": "email_code", "attempts": 0}
    )


class MockEmailAddressesClient:
    """Mock implementation of Clerk's EmailAddresses API, backed by the users the mock stores."""

    def __init__(self, users: MockUsersClient) -> None:
        self._users = users

    def _owner_of(self, email_address_id: str) -> MockUser:
        """Return the user holding an email address, or raise the Clerk not-found error."""

        owner = next(
            (
                user
                for user in self._users._users.values()
                if any(email.id == email_address_id for email in user.email_addresses)
            ),
            None,
        )

        if owner is None:
            raise _create_email_not_found_error(email_address_id)

        return owner

    def _address(self, email_address_id: str) -> MockEmailAddress:
        """Return a stored email address, or raise the Clerk not-found error."""

        owner = self._owner_of(email_address_id)

        return next(email for email in owner.email_addresses if email.id == email_address_id)

    def _attach(self, *, user_id: str, email: str, verified: bool, primary: bool) -> MockEmailAddress:
        """Add an email address to a user, refusing one another user already holds."""

        owner = self._users._get_user_or_error(user_id)
        holder = self._users._emails.get(email.lower())

        if holder is not None and holder != user_id:
            raise _create_email_exists_error(email)

        address = MockEmailAddress.create(email, generate_clerk_id("idn"), verified=verified)
        updates: dict[str, object] = {"email_addresses": [*owner.email_addresses, address]}

        if primary or owner.primary_email_address_id is None:
            updates["primary_email_address_id"] = address.id

        self._users._update_user(user_id, **updates)
        self._users._emails[email.lower()] = user_id

        return address

    def create(
        self,
        *,
        request: (
            models.CreateEmailAddressRequestBody | models.CreateEmailAddressRequestBodyTypedDict | None
        ) = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.EmailAddress:
        """Add an email address to a user."""

        _ = retries, server_url, timeout_ms, http_headers

        return self._attach(
            user_id=get_request_value(request, "user_id"),
            email=get_request_value(request, "email_address"),
            verified=bool(resolve_optional_nullable(get_request_value(request, "verified", UNSET))),
            primary=bool(resolve_optional_nullable(get_request_value(request, "primary", UNSET))),
        )

    def get(
        self,
        *,
        email_address_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.EmailAddress:
        """Get an email address by ID."""

        _ = retries, server_url, timeout_ms, http_headers

        return self._address(email_address_id)

    def delete(
        self,
        *,
        email_address_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.DeletedObject:
        """Remove an email address from its user."""

        _ = retries, server_url, timeout_ms, http_headers

        owner = self._owner_of(email_address_id)
        address = self._address(email_address_id)
        remaining = [email for email in owner.email_addresses if email.id != email_address_id]
        primary = owner.primary_email_address_id

        self._users._update_user(
            owner.id,
            email_addresses=remaining,
            primary_email_address_id=(
                remaining[0].id if primary == email_address_id and remaining else primary
            ),
        )
        self._users._emails.pop(address.email_address.lower(), None)

        return models.DeletedObject(object="email_address", deleted=True, id=email_address_id)

    def update(
        self,
        *,
        email_address_id: str,
        verified: OptionalNullable[bool] = UNSET,
        primary: OptionalNullable[bool] = UNSET,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.EmailAddress:
        """Change whether an email address is verified or primary."""

        _ = retries, server_url, timeout_ms, http_headers

        owner = self._owner_of(email_address_id)
        resolved_verified = resolve_optional_nullable(verified)
        updated = [
            (
                email.model_copy(
                    update={
                        "verification": {
                            "status": VERIFIED_STATUS if resolved_verified else "unverified",
                            "strategy": "email_code",
                        }
                    }
                )
                if email.id == email_address_id and resolved_verified is not None
                else email
            )
            for email in owner.email_addresses
        ]
        updates: dict[str, object] = {"email_addresses": updated}

        if resolve_optional_nullable(primary):
            updates["primary_email_address_id"] = email_address_id

        self._users._update_user(owner.id, **updates)

        return self._address(email_address_id)

    def replace_for_user(
        self,
        *,
        user_id: str,
        email_address: str,
        identification_status: IdentificationStatus | None = IdentificationStatus.VERIFIED,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.EmailAddress:
        """Replace a user's primary email address with a new one."""

        _ = retries, server_url, timeout_ms, http_headers

        owner = self._users._get_user_or_error(user_id)
        previous = owner.primary_email_address_id
        address = self._attach(
            user_id=user_id,
            email=email_address,
            verified=identification_status is IdentificationStatus.VERIFIED,
            primary=True,
        )

        if previous is not None:
            self.delete(email_address_id=previous)

        return address

    def prepare_verification(
        self,
        *,
        email_address_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.VerificationResponse:
        """Start verifying an email address."""

        _ = retries, server_url, timeout_ms, http_headers

        self._address(email_address_id)

        return _build_verification_response("unverified")

    def attempt_verification(
        self,
        *,
        email_address_id: str,
        verification_id: str,
        code: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.VerificationResponse:
        """Complete verifying an email address, accepting any code."""

        _ = verification_id, code, retries, server_url, timeout_ms, http_headers

        self.update(email_address_id=email_address_id, verified=True)

        return _build_verification_response(VERIFIED_STATUS)

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
            models.CreateEmailAddressRequestBody | models.CreateEmailAddressRequestBodyTypedDict | None
        ) = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.EmailAddress:
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
        email_address_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.EmailAddress:
        """Async version of get."""

        return self.get(
            email_address_id=email_address_id,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def delete_async(
        self,
        *,
        email_address_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.DeletedObject:
        """Async version of delete."""

        return self.delete(
            email_address_id=email_address_id,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def update_async(
        self,
        *,
        email_address_id: str,
        verified: OptionalNullable[bool] = UNSET,
        primary: OptionalNullable[bool] = UNSET,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.EmailAddress:
        """Async version of update."""

        return self.update(
            email_address_id=email_address_id,
            verified=verified,
            primary=primary,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def replace_for_user_async(
        self,
        *,
        user_id: str,
        email_address: str,
        identification_status: IdentificationStatus | None = IdentificationStatus.VERIFIED,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.EmailAddress:
        """Async version of replace_for_user."""

        return self.replace_for_user(
            user_id=user_id,
            email_address=email_address,
            identification_status=identification_status,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def prepare_verification_async(
        self,
        *,
        email_address_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.VerificationResponse:
        """Async version of prepare_verification."""

        return self.prepare_verification(
            email_address_id=email_address_id,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def attempt_verification_async(
        self,
        *,
        email_address_id: str,
        verification_id: str,
        code: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.VerificationResponse:
        """Async version of attempt_verification."""

        return self.attempt_verification(
            email_address_id=email_address_id,
            verification_id=verification_id,
            code=code,
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
