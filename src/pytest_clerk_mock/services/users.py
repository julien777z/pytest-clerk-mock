from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, Final, List, Mapping, Tuple

import httpx
from clerk_backend_api import models, utils
from clerk_backend_api.models import ClerkErrors
from clerk_backend_api.models.verifytotpop import CodeType
from clerk_backend_api.types import UNSET, OptionalNullable

from pytest_clerk_mock.models.organization import MockOrganizationMembershipsResponse
from pytest_clerk_mock.models.user import (
    MockEmailAddress,
    MockPhoneNumber,
    MockUser,
)
from pytest_clerk_mock.utils import (
    build_commerce_subscription,
    build_http_response,
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


def _build_oauth_access_token(*, user_id: str, provider: str) -> models.OAuthAccessToken:
    """Build a minimal OAuthAccessToken payload."""

    return models.OAuthAccessToken.model_validate(
        {
            "object": "oauth_access_token",
            "external_account_id": generate_clerk_id("eacct"),
            "provider_user_id": user_id,
            "token": f"token_{generate_clerk_id()}",
            "expires_at": None,
            "provider": provider,
            "public_metadata": {},
            "label": None,
        }
    )


def _build_empty_organization_invitations() -> models.OrganizationInvitationsWithPublicOrganizationData:
    """Build an empty organization invitations response."""

    return models.OrganizationInvitationsWithPublicOrganizationData(
        data=[],
        total_count=0,
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

    def _get_user_or_error(self, user_id: str) -> MockUser:
        """Return a stored user or raise the Clerk not-found error."""

        if user_id not in self._users:
            raise _create_user_not_found_error(user_id)

        return self._users[user_id]

    def _update_user(self, user_id: str, **updates: Any) -> MockUser:
        """Persist a partial user update and return the updated user."""

        user = self._get_user_or_error(user_id)
        updated_user = user.model_copy(update=updates)
        self._users[user_id] = updated_user

        return updated_user

    def _delete_identifiable_items(
        self,
        *,
        user_id: str,
        field_name: str,
        identifier: str,
    ) -> models.DeletedObject:
        """Delete an identifiable item from a user-owned list field."""

        user = self._get_user_or_error(user_id)
        items = getattr(user, field_name)
        filtered_items = [
            item
            for item in items
            if item.get("id") != identifier
            and item.get("external_account_id") != identifier
            and item.get("passkey_identification_id") != identifier
            and item.get("web3_wallet_identification_id") != identifier
        ]

        self._update_user(user_id, **{field_name: filtered_items})

        return models.DeletedObject(object=field_name, deleted=True, id=identifier)

    def _build_instance_organization_memberships_response(
        self,
        *,
        limit: int | None = 10,
        offset: int | None = 0,
    ) -> models.OrganizationMemberships:
        """Build an instance-wide organization memberships response."""

        memberships = [
            membership
            for response in self._memberships.values()
            for membership in response.data
        ]
        resolved_offset = offset or 0
        resolved_limit = limit or 10

        return models.OrganizationMemberships(
            data=memberships[resolved_offset : resolved_offset + resolved_limit],
            total_count=len(memberships),
        )

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
            locale=resolve_optional_nullable(locale),
            email_addresses=email_objects,
            phone_numbers=phone_objects,
            password_enabled=resolve_optional_nullable(password) is not None,
            public_metadata=public_metadata or {},
            private_metadata=private_metadata or {},
            unsafe_metadata=unsafe_metadata or {},
            delete_self_enabled=resolve_optional_nullable(delete_self_enabled) or True,
            create_organization_enabled=resolve_optional_nullable(create_organization_enabled) or True,
            create_organizations_limit=resolve_optional_nullable(create_organizations_limit),
            bypass_client_trust=resolve_optional_nullable(bypass_client_trust) or False,
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

        return self._get_user_or_error(user_id)

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

        self._get_user_or_error(user_id)
        update_data = {
            "external_id": resolve_optional_nullable(external_id),
            "first_name": resolve_optional_nullable(first_name),
            "last_name": resolve_optional_nullable(last_name),
            "locale": resolve_optional_nullable(locale),
            "primary_email_address_id": resolve_optional_nullable(primary_email_address_id),
            "primary_phone_number_id": resolve_optional_nullable(primary_phone_number_id),
            "username": resolve_optional_nullable(username),
            "public_metadata": resolve_optional_nullable(public_metadata),
            "private_metadata": resolve_optional_nullable(private_metadata),
            "unsafe_metadata": resolve_optional_nullable(unsafe_metadata),
            "delete_self_enabled": resolve_optional_nullable(delete_self_enabled),
            "create_organization_enabled": resolve_optional_nullable(create_organization_enabled),
            "create_organizations_limit": resolve_optional_nullable(create_organizations_limit),
            "bypass_client_trust": resolve_optional_nullable(bypass_client_trust),
        }
        update_data = {key: value for key, value in update_data.items() if value is not None}

        if resolve_optional_nullable(password) is not None:
            update_data["password_enabled"] = True

        return self._update_user(user_id, **update_data)

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

        user = self._get_user_or_error(user_id)
        self._users.pop(user_id)

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

    def ban(
        self,
        *,
        user_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.User:
        """Ban a user."""

        _ = retries, server_url, timeout_ms, http_headers

        return self._update_user(user_id, banned=True)

    def bulk_ban(
        self,
        *,
        user_ids: List[str],
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> List[models.User]:
        """Ban multiple users."""

        _ = retries, server_url, timeout_ms, http_headers

        return [self.ban(user_id=user_id) for user_id in user_ids]

    def bulk_unban(
        self,
        *,
        user_ids: List[str],
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> List[models.User]:
        """Unban multiple users."""

        _ = retries, server_url, timeout_ms, http_headers

        return [self.unban(user_id=user_id) for user_id in user_ids]

    def delete_backup_codes(
        self,
        *,
        user_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.DeleteBackupCodeResponseBody:
        """Delete a user's backup codes."""

        _ = retries, server_url, timeout_ms, http_headers
        self._update_user(user_id, backup_code_enabled=False)

        return models.DeleteBackupCodeResponseBody(user_id=user_id)

    def delete_external_account(
        self,
        *,
        user_id: str,
        external_account_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.DeletedObject:
        """Delete an external account from a user."""

        _ = retries, server_url, timeout_ms, http_headers

        return self._delete_identifiable_items(
            user_id=user_id,
            field_name="external_accounts",
            identifier=external_account_id,
        )

    def delete_passkey(
        self,
        *,
        user_id: str,
        passkey_identification_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.DeletedObject:
        """Delete a passkey from a user."""

        _ = retries, server_url, timeout_ms, http_headers

        return self._delete_identifiable_items(
            user_id=user_id,
            field_name="passkeys",
            identifier=passkey_identification_id,
        )

    def delete_profile_image(
        self,
        *,
        user_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.User:
        """Delete a user's profile image."""

        _ = retries, server_url, timeout_ms, http_headers

        return self._update_user(
            user_id,
            has_image=False,
            image_url="",
            profile_image_url="",
        )

    def delete_totp(
        self,
        *,
        user_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.DeleteTOTPResponseBody:
        """Delete a user's TOTP secret."""

        _ = retries, server_url, timeout_ms, http_headers
        self._update_user(user_id, totp_enabled=False)

        return models.DeleteTOTPResponseBody(user_id=user_id)

    def delete_web3_wallet(
        self,
        *,
        user_id: str,
        web3_wallet_identification_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.DeletedObject:
        """Delete a web3 wallet from a user."""

        _ = retries, server_url, timeout_ms, http_headers

        return self._delete_identifiable_items(
            user_id=user_id,
            field_name="web3_wallets",
            identifier=web3_wallet_identification_id,
        )

    def disable_mfa(
        self,
        *,
        user_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.DisableMFAResponseBody:
        """Disable MFA for a user."""

        _ = retries, server_url, timeout_ms, http_headers
        self._update_user(
            user_id,
            two_factor_enabled=False,
            totp_enabled=False,
            backup_code_enabled=False,
        )

        return models.DisableMFAResponseBody(user_id=user_id)

    def do_request(
        self,
        hook_ctx,
        request,
        error_status_codes,
        stream=False,
        retry_config: Tuple[utils.RetryConfig, List[str]] | None = None,
    ) -> httpx.Response:
        """Return a generic successful response for low-level SDK hooks."""

        _ = hook_ctx, request, error_status_codes, stream, retry_config

        return build_http_response()

    def get_billing_subscription(
        self,
        *,
        user_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.CommerceSubscription:
        """Return a placeholder billing subscription for a user."""

        _ = retries, server_url, timeout_ms, http_headers
        self._get_user_or_error(user_id)

        return build_commerce_subscription(payer_id=user_id)

    def get_instance_organization_memberships(
        self,
        *,
        order_by: str | None = None,
        limit: int | None = 10,
        offset: int | None = 0,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.OrganizationMemberships:
        """List organization memberships configured on this mock instance."""

        _ = order_by, retries, server_url, timeout_ms, http_headers

        return self._build_instance_organization_memberships_response(
            limit=limit,
            offset=offset,
        )

    def get_o_auth_access_token(
        self,
        *,
        user_id: str,
        provider: str,
        paginated: bool | None = None,
        limit: int | None = 10,
        offset: int | None = 0,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> List[models.OAuthAccessToken]:
        """Return a placeholder OAuth access token."""

        _ = paginated, limit, offset, retries, server_url, timeout_ms, http_headers
        self._get_user_or_error(user_id)

        return [_build_oauth_access_token(user_id=user_id, provider=provider)]

    def get_organization_invitations(
        self,
        *,
        user_id: str,
        limit: int | None = 10,
        offset: int | None = 0,
        status: models.UsersGetOrganizationInvitationsQueryParamStatus | None = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.OrganizationInvitationsWithPublicOrganizationData:
        """Return the organization invitations for a user."""

        _ = limit, offset, status, retries, server_url, timeout_ms, http_headers
        self._get_user_or_error(user_id)

        return _build_empty_organization_invitations()

    def lock(
        self,
        *,
        user_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.User:
        """Lock a user."""

        _ = retries, server_url, timeout_ms, http_headers

        return self._update_user(user_id, locked=True)

    def set_profile_image(
        self,
        *,
        user_id: str,
        file: models.File | models.FileTypedDict | None = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.User:
        """Set a user's profile image."""

        _ = retries, server_url, timeout_ms, http_headers
        image_name = get_request_value(file or {}, "name") or "profile-image"
        image_url = f"https://img.clerk.mock/{user_id}/{image_name}"

        return self._update_user(
            user_id,
            has_image=True,
            image_url=image_url,
            profile_image_url=image_url,
        )

    def unban(
        self,
        *,
        user_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.User:
        """Unban a user."""

        _ = retries, server_url, timeout_ms, http_headers

        return self._update_user(user_id, banned=False)

    def unlock(
        self,
        *,
        user_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.User:
        """Unlock a user."""

        _ = retries, server_url, timeout_ms, http_headers

        return self._update_user(user_id, locked=False, lockout_expires_in_seconds=None)

    def update_metadata(
        self,
        *,
        user_id: str,
        public_metadata: Dict[str, Any] | None = None,
        private_metadata: Dict[str, Any] | None = None,
        unsafe_metadata: Dict[str, Any] | None = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.User:
        """Merge metadata into a user."""

        _ = retries, server_url, timeout_ms, http_headers
        user = self._get_user_or_error(user_id)
        update_data: dict[str, Any] = {}

        if public_metadata is not None:
            update_data["public_metadata"] = {**user.public_metadata, **public_metadata}

        if private_metadata is not None:
            update_data["private_metadata"] = {**user.private_metadata, **private_metadata}

        if unsafe_metadata is not None:
            update_data["unsafe_metadata"] = {**user.unsafe_metadata, **unsafe_metadata}

        return self._update_user(user_id, **update_data)

    def verify_password(
        self,
        *,
        user_id: str,
        password: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.VerifyPasswordResponseBody:
        """Verify a password against the stored user state."""

        _ = retries, server_url, timeout_ms, http_headers
        user = self._get_user_or_error(user_id)

        return models.VerifyPasswordResponseBody(
            verified=user.password_enabled and bool(password),
        )

    def verify_totp(
        self,
        *,
        user_id: str,
        code: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.VerifyTOTPResponseBody:
        """Verify a TOTP code against the stored user state."""

        _ = retries, server_url, timeout_ms, http_headers
        user = self._get_user_or_error(user_id)

        return models.VerifyTOTPResponseBody(
            verified=user.totp_enabled and bool(code),
            code_type=CodeType.TOTP,
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

    async def ban_async(
        self,
        *,
        user_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.User:
        """Async version of ban."""

        return self.ban(
            user_id=user_id,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def bulk_ban_async(
        self,
        *,
        user_ids: List[str],
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> List[models.User]:
        """Async version of bulk_ban."""

        return self.bulk_ban(
            user_ids=user_ids,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def bulk_unban_async(
        self,
        *,
        user_ids: List[str],
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> List[models.User]:
        """Async version of bulk_unban."""

        return self.bulk_unban(
            user_ids=user_ids,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def delete_backup_codes_async(
        self,
        *,
        user_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.DeleteBackupCodeResponseBody:
        """Async version of delete_backup_codes."""

        return self.delete_backup_codes(
            user_id=user_id,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def delete_external_account_async(
        self,
        *,
        user_id: str,
        external_account_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.DeletedObject:
        """Async version of delete_external_account."""

        return self.delete_external_account(
            user_id=user_id,
            external_account_id=external_account_id,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def delete_passkey_async(
        self,
        *,
        user_id: str,
        passkey_identification_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.DeletedObject:
        """Async version of delete_passkey."""

        return self.delete_passkey(
            user_id=user_id,
            passkey_identification_id=passkey_identification_id,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def delete_profile_image_async(
        self,
        *,
        user_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.User:
        """Async version of delete_profile_image."""

        return self.delete_profile_image(
            user_id=user_id,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def delete_totp_async(
        self,
        *,
        user_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.DeleteTOTPResponseBody:
        """Async version of delete_totp."""

        return self.delete_totp(
            user_id=user_id,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def delete_web3_wallet_async(
        self,
        *,
        user_id: str,
        web3_wallet_identification_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.DeletedObject:
        """Async version of delete_web3_wallet."""

        return self.delete_web3_wallet(
            user_id=user_id,
            web3_wallet_identification_id=web3_wallet_identification_id,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def disable_mfa_async(
        self,
        *,
        user_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.DisableMFAResponseBody:
        """Async version of disable_mfa."""

        return self.disable_mfa(
            user_id=user_id,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def do_request_async(
        self,
        hook_ctx,
        request,
        error_status_codes,
        stream=False,
        retry_config: Tuple[utils.RetryConfig, List[str]] | None = None,
    ) -> httpx.Response:
        """Async version of do_request."""

        return self.do_request(
            hook_ctx,
            request,
            error_status_codes,
            stream=stream,
            retry_config=retry_config,
        )

    async def get_billing_subscription_async(
        self,
        *,
        user_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.CommerceSubscription:
        """Async version of get_billing_subscription."""

        return self.get_billing_subscription(
            user_id=user_id,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def get_instance_organization_memberships_async(
        self,
        *,
        order_by: str | None = None,
        limit: int | None = 10,
        offset: int | None = 0,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.OrganizationMemberships:
        """Async version of get_instance_organization_memberships."""

        return self.get_instance_organization_memberships(
            order_by=order_by,
            limit=limit,
            offset=offset,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def get_o_auth_access_token_async(
        self,
        *,
        user_id: str,
        provider: str,
        paginated: bool | None = None,
        limit: int | None = 10,
        offset: int | None = 0,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> List[models.OAuthAccessToken]:
        """Async version of get_o_auth_access_token."""

        return self.get_o_auth_access_token(
            user_id=user_id,
            provider=provider,
            paginated=paginated,
            limit=limit,
            offset=offset,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def get_organization_invitations_async(
        self,
        *,
        user_id: str,
        limit: int | None = 10,
        offset: int | None = 0,
        status: models.UsersGetOrganizationInvitationsQueryParamStatus | None = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.OrganizationInvitationsWithPublicOrganizationData:
        """Async version of get_organization_invitations."""

        return self.get_organization_invitations(
            user_id=user_id,
            limit=limit,
            offset=offset,
            status=status,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def lock_async(
        self,
        *,
        user_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.User:
        """Async version of lock."""

        return self.lock(
            user_id=user_id,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def set_profile_image_async(
        self,
        *,
        user_id: str,
        file: models.File | models.FileTypedDict | None = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.User:
        """Async version of set_profile_image."""

        return self.set_profile_image(
            user_id=user_id,
            file=file,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def unban_async(
        self,
        *,
        user_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.User:
        """Async version of unban."""

        return self.unban(
            user_id=user_id,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def unlock_async(
        self,
        *,
        user_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.User:
        """Async version of unlock."""

        return self.unlock(
            user_id=user_id,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def update_metadata_async(
        self,
        *,
        user_id: str,
        public_metadata: Dict[str, Any] | None = None,
        private_metadata: Dict[str, Any] | None = None,
        unsafe_metadata: Dict[str, Any] | None = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.User:
        """Async version of update_metadata."""

        return self.update_metadata(
            user_id=user_id,
            public_metadata=public_metadata,
            private_metadata=private_metadata,
            unsafe_metadata=unsafe_metadata,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def verify_password_async(
        self,
        *,
        user_id: str,
        password: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.VerifyPasswordResponseBody:
        """Async version of verify_password."""

        return self.verify_password(
            user_id=user_id,
            password=password,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def verify_totp_async(
        self,
        *,
        user_id: str,
        code: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.VerifyTOTPResponseBody:
        """Async version of verify_totp."""

        return self.verify_totp(
            user_id=user_id,
            code=code,
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
