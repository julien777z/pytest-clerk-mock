from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, Final, List, Mapping

from clerk_backend_api import models, utils
from clerk_backend_api.models import ClerkErrors
from clerk_backend_api.types import UNSET, OptionalNullable
from pydantic import BaseModel, Field

from pytest_clerk_mock.models.organization import MockOrganizationMembershipsResponse
from pytest_clerk_mock.models.user import MockEmailAddress, MockPhoneNumber, MockUser
from pytest_clerk_mock.utils import (
    create_clerk_error,
    generate_clerk_id,
    get_request_value,
    resolve_optional_nullable,
)

EMAIL_EXISTS_ERROR_CODE: Final[str] = "form_identifier_exists"
RESOURCE_NOT_FOUND_ERROR_CODE: Final[str] = "resource_not_found"
EMAIL_EXISTS_MESSAGE: Final[str] = "That email address is taken. Please try another."
EMAIL_EXISTS_RESPONSE_TEXT: Final[str] = "That email address is taken."
USER_NOT_FOUND_RESPONSE_TEXT: Final[str] = "User not found."
DEFAULT_GET_USER_LIST_REQUEST: Final[models.GetUserListRequest] = models.GetUserListRequest()


class MockListResponse(BaseModel):
    """Response wrapper for list operations, matching Clerk SDK structure."""

    data: list[MockUser] = Field(default_factory=list)


def _create_email_exists_error(email: str) -> ClerkErrors:
    """Create a ClerkErrors exception for duplicate email."""

    return create_clerk_error(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        response_text=EMAIL_EXISTS_RESPONSE_TEXT,
        code=EMAIL_EXISTS_ERROR_CODE,
        message=EMAIL_EXISTS_MESSAGE,
    )


def _create_user_not_found_error(user_id: str) -> ClerkErrors:
    """Create a ClerkErrors exception for missing users."""

    return create_clerk_error(
        status_code=HTTPStatus.NOT_FOUND,
        response_text=USER_NOT_FOUND_RESPONSE_TEXT,
        code=RESOURCE_NOT_FOUND_ERROR_CODE,
        message=f"User not found: {user_id}",
    )


class MockUsersClient:
    """Mock implementation of Clerk's Users API."""

    def __init__(self) -> None:
        self._users: dict[str, MockUser] = {}
        self._emails: dict[str, str] = {}
        self._memberships: dict[str, MockOrganizationMembershipsResponse] = {}

    def reset(self) -> None:
        """Clear all stored users and email mappings."""

        self._users.clear()
        self._emails.clear()
        self._memberships.clear()

    def create(
        self,
        *,
        external_id: OptionalNullable[str] = UNSET,
        first_name: OptionalNullable[str] = UNSET,
        last_name: OptionalNullable[str] = UNSET,
        locale: OptionalNullable[str] = UNSET,
        email_address: List[str] | None = None,
        phone_number: List[str] | None = None,
        web3_wallet: List[str] | None = None,
        username: OptionalNullable[str] = UNSET,
        password: OptionalNullable[str] = UNSET,
        password_digest: OptionalNullable[str] = UNSET,
        password_hasher: str | None = None,
        skip_password_checks: OptionalNullable[bool] = UNSET,
        skip_password_requirement: OptionalNullable[bool] = UNSET,
        totp_secret: OptionalNullable[str] = UNSET,
        backup_codes: List[str] | None = None,
        public_metadata: Dict[str, Any] | None = None,
        private_metadata: Dict[str, Any] | None = None,
        unsafe_metadata: Dict[str, Any] | None = None,
        delete_self_enabled: OptionalNullable[bool] = UNSET,
        legal_accepted_at: OptionalNullable[str] = UNSET,
        skip_legal_checks: OptionalNullable[bool] = UNSET,
        create_organization_enabled: OptionalNullable[bool] = UNSET,
        create_organizations_limit: OptionalNullable[int] = UNSET,
        created_at: OptionalNullable[str] = UNSET,
        bypass_client_trust: OptionalNullable[bool] = UNSET,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.User:
        """Create a new user."""

        _ = (
            locale,
            web3_wallet,
            password_digest,
            password_hasher,
            skip_password_checks,
            skip_password_requirement,
            totp_secret,
            backup_codes,
            legal_accepted_at,
            skip_legal_checks,
            created_at,
            bypass_client_trust,
            retries,
            server_url,
            timeout_ms,
            http_headers,
        )

        if email_address:
            for email in email_address:
                if email.lower() in self._emails:
                    raise _create_email_exists_error(email)

        user_id = generate_clerk_id("user")
        email_objects: list[MockEmailAddress] = []
        primary_email_id: str | None = None

        if email_address:
            for index, email in enumerate(email_address):
                email_id = generate_clerk_id("idn")
                email_obj = MockEmailAddress.create(email=email, email_id=email_id)
                email_objects.append(email_obj)
                self._emails[email.lower()] = user_id

                if index == 0:
                    primary_email_id = email_id

        phone_objects: list[MockPhoneNumber] = []
        primary_phone_id: str | None = None

        if phone_number:
            for index, phone in enumerate(phone_number):
                phone_id = generate_clerk_id("idn")
                phone_obj = MockPhoneNumber.create(phone=phone, phone_id=phone_id)
                phone_objects.append(phone_obj)

                if index == 0:
                    primary_phone_id = phone_id

        user = MockUser(
            id=user_id,
            external_id=resolve_optional_nullable(external_id),
            primary_email_address_id=primary_email_id,
            primary_phone_number_id=primary_phone_id,
            username=resolve_optional_nullable(username),
            first_name=resolve_optional_nullable(first_name),
            last_name=resolve_optional_nullable(last_name),
            email_addresses=email_objects,
            phone_numbers=phone_objects,
            password_enabled=resolve_optional_nullable(password) is not None,
            public_metadata=public_metadata or {},
            private_metadata=private_metadata or {},
            unsafe_metadata=unsafe_metadata or {},
            delete_self_enabled=resolve_optional_nullable(delete_self_enabled) or True,
            create_organization_enabled=resolve_optional_nullable(create_organization_enabled) or True,
            create_organizations_limit=resolve_optional_nullable(create_organizations_limit),
        )

        self._users[user_id] = user

        return user

    def get(
        self,
        *,
        user_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.User:
        """Get a user by ID."""

        _ = retries, server_url, timeout_ms, http_headers

        if user_id not in self._users:
            raise _create_user_not_found_error(user_id)

        return self._users[user_id]

    def list(
        self,
        *,
        request: models.GetUserListRequest
        | models.GetUserListRequestTypedDict = DEFAULT_GET_USER_LIST_REQUEST,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> List[models.User]:
        """List users with optional filters."""

        _ = retries, server_url, timeout_ms, http_headers
        users = list(self._users.values())

        email_address = get_request_value(request, "email_address")
        phone_number = get_request_value(request, "phone_number")
        external_id = get_request_value(request, "external_id")
        username = get_request_value(request, "username")
        web3_wallet = get_request_value(request, "web3_wallet")
        user_id = get_request_value(request, "user_id")
        organization_id = get_request_value(request, "organization_id")
        query = get_request_value(request, "query")
        email_address_query = get_request_value(request, "email_address_query")
        phone_number_query = get_request_value(request, "phone_number_query")
        username_query = get_request_value(request, "username_query")
        name_query = get_request_value(request, "name_query")
        banned = get_request_value(request, "banned")
        last_active_at_before = get_request_value(request, "last_active_at_before")
        last_active_at_after = get_request_value(request, "last_active_at_after")
        last_active_at_since = get_request_value(request, "last_active_at_since")
        created_at_before = get_request_value(request, "created_at_before")
        created_at_after = get_request_value(request, "created_at_after")
        limit = get_request_value(request, "limit")
        offset = get_request_value(request, "offset")
        order_by = get_request_value(request, "order_by")

        if email_address:
            email_set = {email.lower() for email in email_address}
            users = [
                user
                for user in users
                if any(email.email_address.lower() in email_set for email in user.email_addresses)
            ]

        if phone_number:
            phone_set = set(phone_number)
            users = [
                user for user in users if any(phone.phone_number in phone_set for phone in user.phone_numbers)
            ]

        if external_id:
            external_id_set = set(external_id)
            users = [user for user in users if user.external_id in external_id_set]

        if username:
            username_set = set(username)
            users = [user for user in users if user.username in username_set]

        if web3_wallet:
            wallet_set = set(web3_wallet)
            users = [
                user
                for user in users
                if any(wallet.get("web3_wallet") in wallet_set for wallet in user.web3_wallets)
            ]

        if user_id:
            user_id_set = set(user_id)
            users = [user for user in users if user.id in user_id_set]

        if organization_id:
            organization_id_set = set(organization_id)
            users = [
                user
                for user in users
                if any(
                    membership.organization_id in organization_id_set
                    for membership in self._memberships.get(
                        user.id,
                        MockOrganizationMembershipsResponse(data=[], total_count=0),
                    ).data
                )
            ]

        if query:
            query_lower = query.lower()
            users = [
                user
                for user in users
                if (user.first_name and query_lower in user.first_name.lower())
                or (user.last_name and query_lower in user.last_name.lower())
                or (user.username and query_lower in user.username.lower())
                or any(query_lower in email.email_address.lower() for email in user.email_addresses)
            ]

        if email_address_query:
            normalized_query = email_address_query.lower()
            users = [
                user
                for user in users
                if any(normalized_query in email.email_address.lower() for email in user.email_addresses)
            ]

        if phone_number_query:
            normalized_query = phone_number_query.lower()
            users = [
                user
                for user in users
                if any(normalized_query in phone.phone_number.lower() for phone in user.phone_numbers)
            ]

        if username_query:
            normalized_query = username_query.lower()
            users = [
                user
                for user in users
                if user.username is not None and normalized_query in user.username.lower()
            ]

        if name_query:
            normalized_query = name_query.lower()
            users = [
                user
                for user in users
                if (user.first_name and normalized_query in user.first_name.lower())
                or (user.last_name and normalized_query in user.last_name.lower())
            ]

        if banned is not None:
            users = [user for user in users if user.banned is banned]

        if last_active_at_before is not None:
            users = [
                user
                for user in users
                if user.last_active_at is not None and user.last_active_at < last_active_at_before
            ]

        if last_active_at_after is not None:
            users = [
                user
                for user in users
                if user.last_active_at is not None and user.last_active_at > last_active_at_after
            ]

        if last_active_at_since is not None:
            users = [
                user
                for user in users
                if user.last_active_at is not None and user.last_active_at >= last_active_at_since
            ]

        if created_at_before is not None:
            users = [user for user in users if user.created_at < created_at_before]

        if created_at_after is not None:
            users = [user for user in users if user.created_at > created_at_after]

        resolved_order_by = order_by or "-created_at"
        reverse = resolved_order_by.startswith("-")
        sort_key = resolved_order_by.lstrip("-+")

        if sort_key == "created_at":
            users.sort(key=lambda user: user.created_at, reverse=reverse)
        elif sort_key == "updated_at":
            users.sort(key=lambda user: user.updated_at, reverse=reverse)

        resolved_offset = offset or 0
        resolved_limit = limit or 10

        return users[resolved_offset : resolved_offset + resolved_limit]

    def update(
        self,
        *,
        user_id: str,
        external_id: OptionalNullable[str] = UNSET,
        first_name: OptionalNullable[str] = UNSET,
        last_name: OptionalNullable[str] = UNSET,
        locale: OptionalNullable[str] = UNSET,
        primary_email_address_id: OptionalNullable[str] = UNSET,
        notify_primary_email_address_changed: OptionalNullable[bool] = False,
        primary_phone_number_id: OptionalNullable[str] = UNSET,
        primary_web3_wallet_id: OptionalNullable[str] = UNSET,
        username: OptionalNullable[str] = UNSET,
        profile_image_id: OptionalNullable[str] = UNSET,
        password: OptionalNullable[str] = UNSET,
        password_digest: str | None = None,
        password_hasher: str | None = None,
        skip_password_checks: OptionalNullable[bool] = UNSET,
        sign_out_of_other_sessions: OptionalNullable[bool] = UNSET,
        totp_secret: OptionalNullable[str] = UNSET,
        backup_codes: List[str] | None = None,
        public_metadata: OptionalNullable[Dict[str, Any]] = UNSET,
        private_metadata: OptionalNullable[Dict[str, Any]] = UNSET,
        unsafe_metadata: OptionalNullable[Dict[str, Any]] = UNSET,
        delete_self_enabled: OptionalNullable[bool] = UNSET,
        create_organization_enabled: OptionalNullable[bool] = UNSET,
        legal_accepted_at: OptionalNullable[str] = UNSET,
        skip_legal_checks: OptionalNullable[bool] = UNSET,
        create_organizations_limit: OptionalNullable[int] = UNSET,
        created_at: OptionalNullable[str] = UNSET,
        bypass_client_trust: OptionalNullable[bool] = UNSET,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.User:
        """Update a user by ID."""

        _ = (
            locale,
            notify_primary_email_address_changed,
            primary_web3_wallet_id,
            profile_image_id,
            password_digest,
            password_hasher,
            skip_password_checks,
            sign_out_of_other_sessions,
            totp_secret,
            backup_codes,
            legal_accepted_at,
            skip_legal_checks,
            created_at,
            bypass_client_trust,
            retries,
            server_url,
            timeout_ms,
            http_headers,
        )

        if user_id not in self._users:
            raise _create_user_not_found_error(user_id)

        user = self._users[user_id]
        update_data = {
            "external_id": resolve_optional_nullable(external_id),
            "first_name": resolve_optional_nullable(first_name),
            "last_name": resolve_optional_nullable(last_name),
            "primary_email_address_id": resolve_optional_nullable(primary_email_address_id),
            "primary_phone_number_id": resolve_optional_nullable(primary_phone_number_id),
            "username": resolve_optional_nullable(username),
            "public_metadata": resolve_optional_nullable(public_metadata),
            "private_metadata": resolve_optional_nullable(private_metadata),
            "unsafe_metadata": resolve_optional_nullable(unsafe_metadata),
            "delete_self_enabled": resolve_optional_nullable(delete_self_enabled),
            "create_organization_enabled": resolve_optional_nullable(create_organization_enabled),
            "create_organizations_limit": resolve_optional_nullable(create_organizations_limit),
        }
        update_data = {key: value for key, value in update_data.items() if value is not None}

        if resolve_optional_nullable(password) is not None:
            update_data["password_enabled"] = True

        updated_user = user.model_copy(update=update_data)
        self._users[user_id] = updated_user

        return updated_user

    def delete(
        self,
        *,
        user_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.DeletedObject:
        """Delete a user by ID."""

        _ = retries, server_url, timeout_ms, http_headers

        if user_id not in self._users:
            raise _create_user_not_found_error(user_id)

        user = self._users.pop(user_id)

        for email in user.email_addresses:
            self._emails.pop(email.email_address.lower(), None)

        return models.DeletedObject(object="user", deleted=True, id=user.id)

    def count(
        self,
        *,
        email_address: List[str] | None = None,
        phone_number: List[str] | None = None,
        external_id: List[str] | None = None,
        username: List[str] | None = None,
        web3_wallet: List[str] | None = None,
        user_id: List[str] | None = None,
        organization_id: List[str] | None = None,
        query: str | None = None,
        email_address_query: str | None = None,
        phone_number_query: str | None = None,
        username_query: str | None = None,
        name_query: str | None = None,
        banned: bool | None = None,
        last_active_at_before: int | None = None,
        last_active_at_after: int | None = None,
        last_active_at_since: int | None = None,
        created_at_before: int | None = None,
        created_at_after: int | None = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.TotalCount:
        """Count users matching the filters."""

        _ = retries, server_url, timeout_ms, http_headers
        users = self.list(
            request=models.GetUserListRequest(
                email_address=email_address,
                phone_number=phone_number,
                external_id=external_id,
                username=username,
                web3_wallet=web3_wallet,
                user_id=user_id,
                organization_id=organization_id,
                query=query,
                email_address_query=email_address_query,
                phone_number_query=phone_number_query,
                username_query=username_query,
                name_query=name_query,
                banned=banned,
                last_active_at_before=last_active_at_before,
                last_active_at_after=last_active_at_after,
                last_active_at_since=last_active_at_since,
                created_at_before=created_at_before,
                created_at_after=created_at_after,
                limit=999999,
            ),
        )

        return models.TotalCount(
            object=models.TotalCountObject.TOTAL_COUNT,
            total_count=len(users),
        )

    def set_organization_memberships(
        self,
        user_id: str,
        memberships: MockOrganizationMembershipsResponse,
    ) -> None:
        """Configure organization memberships for a user."""

        self._memberships[user_id] = memberships

    def get_organization_memberships(
        self,
        *,
        user_id: str,
        limit: int | None = 10,
        offset: int | None = 0,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.OrganizationMemberships:
        """Get organization memberships for a user (sync version)."""

        _ = limit, offset, retries, server_url, timeout_ms, http_headers

        return self._memberships.get(
            user_id,
            MockOrganizationMembershipsResponse(data=[], total_count=0),
        )

    async def get_organization_memberships_async(
        self,
        *,
        user_id: str,
        limit: int | None = 10,
        offset: int | None = 0,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.OrganizationMemberships:
        """Get organization memberships for a user (async version)."""

        return self.get_organization_memberships(
            user_id=user_id,
            limit=limit,
            offset=offset,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def create_async(
        self,
        *,
        external_id: OptionalNullable[str] = UNSET,
        first_name: OptionalNullable[str] = UNSET,
        last_name: OptionalNullable[str] = UNSET,
        locale: OptionalNullable[str] = UNSET,
        email_address: List[str] | None = None,
        phone_number: List[str] | None = None,
        web3_wallet: List[str] | None = None,
        username: OptionalNullable[str] = UNSET,
        password: OptionalNullable[str] = UNSET,
        password_digest: OptionalNullable[str] = UNSET,
        password_hasher: str | None = None,
        skip_password_checks: OptionalNullable[bool] = UNSET,
        skip_password_requirement: OptionalNullable[bool] = UNSET,
        totp_secret: OptionalNullable[str] = UNSET,
        backup_codes: List[str] | None = None,
        public_metadata: Dict[str, Any] | None = None,
        private_metadata: Dict[str, Any] | None = None,
        unsafe_metadata: Dict[str, Any] | None = None,
        delete_self_enabled: OptionalNullable[bool] = UNSET,
        legal_accepted_at: OptionalNullable[str] = UNSET,
        skip_legal_checks: OptionalNullable[bool] = UNSET,
        create_organization_enabled: OptionalNullable[bool] = UNSET,
        create_organizations_limit: OptionalNullable[int] = UNSET,
        created_at: OptionalNullable[str] = UNSET,
        bypass_client_trust: OptionalNullable[bool] = UNSET,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.User:
        """Async version of create."""

        return self.create(
            external_id=external_id,
            first_name=first_name,
            last_name=last_name,
            locale=locale,
            email_address=email_address,
            phone_number=phone_number,
            web3_wallet=web3_wallet,
            username=username,
            password=password,
            password_digest=password_digest,
            password_hasher=password_hasher,
            skip_password_checks=skip_password_checks,
            skip_password_requirement=skip_password_requirement,
            totp_secret=totp_secret,
            backup_codes=backup_codes,
            public_metadata=public_metadata,
            private_metadata=private_metadata,
            unsafe_metadata=unsafe_metadata,
            delete_self_enabled=delete_self_enabled,
            legal_accepted_at=legal_accepted_at,
            skip_legal_checks=skip_legal_checks,
            create_organization_enabled=create_organization_enabled,
            create_organizations_limit=create_organizations_limit,
            created_at=created_at,
            bypass_client_trust=bypass_client_trust,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def get_async(
        self,
        *,
        user_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.User:
        """Async version of get."""

        return self.get(
            user_id=user_id,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def list_async(
        self,
        *,
        request: models.GetUserListRequest
        | models.GetUserListRequestTypedDict = DEFAULT_GET_USER_LIST_REQUEST,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> List[models.User]:
        """Async version of list."""

        return self.list(
            request=request,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def update_async(
        self,
        *,
        user_id: str,
        external_id: OptionalNullable[str] = UNSET,
        first_name: OptionalNullable[str] = UNSET,
        last_name: OptionalNullable[str] = UNSET,
        locale: OptionalNullable[str] = UNSET,
        primary_email_address_id: OptionalNullable[str] = UNSET,
        notify_primary_email_address_changed: OptionalNullable[bool] = False,
        primary_phone_number_id: OptionalNullable[str] = UNSET,
        primary_web3_wallet_id: OptionalNullable[str] = UNSET,
        username: OptionalNullable[str] = UNSET,
        profile_image_id: OptionalNullable[str] = UNSET,
        password: OptionalNullable[str] = UNSET,
        password_digest: str | None = None,
        password_hasher: str | None = None,
        skip_password_checks: OptionalNullable[bool] = UNSET,
        sign_out_of_other_sessions: OptionalNullable[bool] = UNSET,
        totp_secret: OptionalNullable[str] = UNSET,
        backup_codes: List[str] | None = None,
        public_metadata: OptionalNullable[Dict[str, Any]] = UNSET,
        private_metadata: OptionalNullable[Dict[str, Any]] = UNSET,
        unsafe_metadata: OptionalNullable[Dict[str, Any]] = UNSET,
        delete_self_enabled: OptionalNullable[bool] = UNSET,
        create_organization_enabled: OptionalNullable[bool] = UNSET,
        legal_accepted_at: OptionalNullable[str] = UNSET,
        skip_legal_checks: OptionalNullable[bool] = UNSET,
        create_organizations_limit: OptionalNullable[int] = UNSET,
        created_at: OptionalNullable[str] = UNSET,
        bypass_client_trust: OptionalNullable[bool] = UNSET,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.User:
        """Async version of update."""

        return self.update(
            user_id=user_id,
            external_id=external_id,
            first_name=first_name,
            last_name=last_name,
            locale=locale,
            primary_email_address_id=primary_email_address_id,
            notify_primary_email_address_changed=notify_primary_email_address_changed,
            primary_phone_number_id=primary_phone_number_id,
            primary_web3_wallet_id=primary_web3_wallet_id,
            username=username,
            profile_image_id=profile_image_id,
            password=password,
            password_digest=password_digest,
            password_hasher=password_hasher,
            skip_password_checks=skip_password_checks,
            sign_out_of_other_sessions=sign_out_of_other_sessions,
            totp_secret=totp_secret,
            backup_codes=backup_codes,
            public_metadata=public_metadata,
            private_metadata=private_metadata,
            unsafe_metadata=unsafe_metadata,
            delete_self_enabled=delete_self_enabled,
            create_organization_enabled=create_organization_enabled,
            legal_accepted_at=legal_accepted_at,
            skip_legal_checks=skip_legal_checks,
            create_organizations_limit=create_organizations_limit,
            created_at=created_at,
            bypass_client_trust=bypass_client_trust,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def delete_async(
        self,
        *,
        user_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.DeletedObject:
        """Async version of delete."""

        return self.delete(
            user_id=user_id,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def count_async(
        self,
        *,
        email_address: List[str] | None = None,
        phone_number: List[str] | None = None,
        external_id: List[str] | None = None,
        username: List[str] | None = None,
        web3_wallet: List[str] | None = None,
        user_id: List[str] | None = None,
        organization_id: List[str] | None = None,
        query: str | None = None,
        email_address_query: str | None = None,
        phone_number_query: str | None = None,
        username_query: str | None = None,
        name_query: str | None = None,
        banned: bool | None = None,
        last_active_at_before: int | None = None,
        last_active_at_after: int | None = None,
        last_active_at_since: int | None = None,
        created_at_before: int | None = None,
        created_at_after: int | None = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.TotalCount:
        """Async version of count."""

        return self.count(
            email_address=email_address,
            phone_number=phone_number,
            external_id=external_id,
            username=username,
            web3_wallet=web3_wallet,
            user_id=user_id,
            organization_id=organization_id,
            query=query,
            email_address_query=email_address_query,
            phone_number_query=phone_number_query,
            username_query=username_query,
            name_query=name_query,
            banned=banned,
            last_active_at_before=last_active_at_before,
            last_active_at_after=last_active_at_after,
            last_active_at_since=last_active_at_since,
            created_at_before=created_at_before,
            created_at_after=created_at_after,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )
