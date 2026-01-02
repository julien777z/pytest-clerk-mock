from __future__ import annotations

import secrets
from typing import Any
from unittest.mock import MagicMock

import httpx
from clerk_backend_api.models import ClerkErrors
from clerk_backend_api.models.clerkerror import ClerkError
from clerk_backend_api.models.clerkerrors import ClerkErrorsData
from pydantic import BaseModel, Field

from pytest_clerk_mock.models.organization import MockOrganizationMembershipsResponse
from pytest_clerk_mock.models.user import MockEmailAddress, MockPhoneNumber, MockUser

EMAIL_EXISTS_ERROR_CODE = "form_identifier_exists"


class UserNotFoundError(Exception):
    """Raised when a user is not found."""

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        super().__init__(f"User not found: {user_id}")


class MockListResponse(BaseModel):
    """Response wrapper for list operations, matching Clerk SDK structure."""

    data: list[MockUser] = Field(default_factory=list)


def _generate_id(prefix: str) -> str:
    """Generate a Clerk-style ID with given prefix."""

    return f"{prefix}_{secrets.token_hex(12)}"


def _create_email_exists_error(email: str) -> ClerkErrors:
    """Create a ClerkErrors exception for duplicate email."""

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 422
    mock_response.text = "That email address is taken."
    mock_response.headers = httpx.Headers({})

    return ClerkErrors(
        data=ClerkErrorsData(
            errors=[
                ClerkError(
                    code=EMAIL_EXISTS_ERROR_CODE,
                    message="That email address is taken. Please try another.",
                    long_message="That email address is taken. Please try another.",
                )
            ]
        ),
        raw_response=mock_response,
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
        email_address: list[str] | None = None,
        phone_number: list[str] | None = None,
        username: str | None = None,
        password: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        external_id: str | None = None,
        public_metadata: dict[str, Any] | None = None,
        private_metadata: dict[str, Any] | None = None,
        unsafe_metadata: dict[str, Any] | None = None,
        skip_password_checks: bool = False,
        skip_password_requirement: bool = False,
        totp_secret: str | None = None,
        backup_codes: list[str] | None = None,
        created_at: str | None = None,
    ) -> MockUser:
        """Create a new user."""

        if email_address:
            for email in email_address:
                if email.lower() in self._emails:
                    raise _create_email_exists_error(email)

        user_id = _generate_id("user")
        email_objects: list[MockEmailAddress] = []
        primary_email_id: str | None = None

        if email_address:
            for i, email in enumerate(email_address):
                email_id = _generate_id("idn")
                email_obj = MockEmailAddress.create(email=email, email_id=email_id)
                email_objects.append(email_obj)
                self._emails[email.lower()] = user_id

                if i == 0:
                    primary_email_id = email_id

        phone_objects: list[MockPhoneNumber] = []
        primary_phone_id: str | None = None

        if phone_number:
            for i, phone in enumerate(phone_number):
                phone_id = _generate_id("idn")
                phone_obj = MockPhoneNumber.create(phone=phone, phone_id=phone_id)
                phone_objects.append(phone_obj)

                if i == 0:
                    primary_phone_id = phone_id

        user = MockUser(
            id=user_id,
            external_id=external_id,
            primary_email_address_id=primary_email_id,
            primary_phone_number_id=primary_phone_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            email_addresses=email_objects,
            phone_numbers=phone_objects,
            password_enabled=password is not None,
            public_metadata=public_metadata or {},
            private_metadata=private_metadata or {},
            unsafe_metadata=unsafe_metadata or {},
        )

        self._users[user_id] = user

        return user

    def get(self, user_id: str) -> MockUser:
        """Get a user by ID."""

        if user_id not in self._users:
            raise UserNotFoundError(user_id)

        return self._users[user_id]

    def list(
        self,
        *,
        email_address: list[str] | None = None,
        phone_number: list[str] | None = None,
        external_id: list[str] | None = None,
        username: list[str] | None = None,
        user_id: list[str] | None = None,
        query: str | None = None,
        last_active_at_since: int | None = None,
        limit: int = 10,
        offset: int = 0,
        order_by: str = "-created_at",
    ) -> list[MockUser]:
        """List users with optional filters."""

        users = list(self._users.values())

        if email_address:
            email_set = {e.lower() for e in email_address}
            users = [
                u
                for u in users
                if any(e.email_address.lower() in email_set for e in u.email_addresses)
            ]

        if phone_number:
            phone_set = set(phone_number)
            users = [
                u
                for u in users
                if any(p.phone_number in phone_set for p in u.phone_numbers)
            ]

        if external_id:
            ext_id_set = set(external_id)
            users = [u for u in users if u.external_id in ext_id_set]

        if username:
            username_set = set(username)
            users = [u for u in users if u.username in username_set]

        if user_id:
            user_id_set = set(user_id)
            users = [u for u in users if u.id in user_id_set]

        if query:
            query_lower = query.lower()
            users = [
                u
                for u in users
                if (u.first_name and query_lower in u.first_name.lower())
                or (u.last_name and query_lower in u.last_name.lower())
                or (u.username and query_lower in u.username.lower())
                or any(
                    query_lower in e.email_address.lower() for e in u.email_addresses
                )
            ]

        reverse = order_by.startswith("-")
        sort_key = order_by.lstrip("-+")

        if sort_key == "created_at":
            users.sort(key=lambda u: u.created_at, reverse=reverse)
        elif sort_key == "updated_at":
            users.sort(key=lambda u: u.updated_at, reverse=reverse)

        return users[offset : offset + limit]

    def update(
        self,
        user_id: str,
        *,
        external_id: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        username: str | None = None,
        password: str | None = None,
        primary_email_address_id: str | None = None,
        primary_phone_number_id: str | None = None,
        public_metadata: dict[str, Any] | None = None,
        private_metadata: dict[str, Any] | None = None,
        unsafe_metadata: dict[str, Any] | None = None,
        profile_image_id: str | None = None,
        skip_password_checks: bool = False,
        sign_out_of_other_sessions: bool = False,
        totp_secret: str | None = None,
        backup_codes: list[str] | None = None,
        delete_self_enabled: bool | None = None,
        create_organization_enabled: bool | None = None,
        notify_primary_email_address_changed: bool = False,
    ) -> MockUser:
        """Update a user by ID."""

        if user_id not in self._users:
            raise UserNotFoundError(user_id)

        user = self._users[user_id]
        fields = {
            "external_id": external_id,
            "first_name": first_name,
            "last_name": last_name,
            "username": username,
            "primary_email_address_id": primary_email_address_id,
            "primary_phone_number_id": primary_phone_number_id,
            "public_metadata": public_metadata,
            "private_metadata": private_metadata,
            "unsafe_metadata": unsafe_metadata,
            "delete_self_enabled": delete_self_enabled,
            "create_organization_enabled": create_organization_enabled,
        }
        update_data = {k: v for k, v in fields.items() if v is not None}

        if password is not None:
            update_data["password_enabled"] = True

        updated_user = user.model_copy(update=update_data)
        self._users[user_id] = updated_user

        return updated_user

    def delete(self, user_id: str) -> MockUser:
        """Delete a user by ID."""

        if user_id not in self._users:
            raise UserNotFoundError(user_id)

        user = self._users.pop(user_id)

        for email in user.email_addresses:
            self._emails.pop(email.email_address.lower(), None)

        return user

    def count(
        self,
        *,
        email_address: list[str] | None = None,
        phone_number: list[str] | None = None,
        external_id: list[str] | None = None,
        username: list[str] | None = None,
        user_id: list[str] | None = None,
        query: str | None = None,
    ) -> int:
        """Count users matching the filters."""

        users = self.list(
            email_address=email_address,
            phone_number=phone_number,
            external_id=external_id,
            username=username,
            user_id=user_id,
            query=query,
            limit=999999,
        )

        return len(users)

    def set_organization_memberships(
        self,
        user_id: str,
        memberships: MockOrganizationMembershipsResponse,
    ) -> None:
        """Configure organization memberships for a user."""

        self._memberships[user_id] = memberships

    def get_organization_memberships(
        self,
        user_id: str,
        *,
        limit: int | None = 10,
        offset: int | None = 0,
    ) -> MockOrganizationMembershipsResponse:
        """Get organization memberships for a user (sync version)."""

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
    ) -> MockOrganizationMembershipsResponse:
        """Get organization memberships for a user (async version)."""

        return self.get_organization_memberships(user_id, limit=limit, offset=offset)

    async def create_async(
        self,
        *,
        email_address: list[str] | None = None,
        phone_number: list[str] | None = None,
        username: str | None = None,
        password: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        external_id: str | None = None,
        public_metadata: dict[str, Any] | None = None,
        private_metadata: dict[str, Any] | None = None,
        unsafe_metadata: dict[str, Any] | None = None,
        skip_password_checks: bool = False,
        skip_password_requirement: bool = False,
        totp_secret: str | None = None,
        backup_codes: list[str] | None = None,
        created_at: str | None = None,
    ) -> MockUser:
        """Async version of create."""

        return self.create(
            email_address=email_address,
            phone_number=phone_number,
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            external_id=external_id,
            public_metadata=public_metadata,
            private_metadata=private_metadata,
            unsafe_metadata=unsafe_metadata,
            skip_password_checks=skip_password_checks,
            skip_password_requirement=skip_password_requirement,
            totp_secret=totp_secret,
            backup_codes=backup_codes,
            created_at=created_at,
        )

    async def get_async(self, *, user_id: str) -> MockUser:
        """Async version of get."""

        return self.get(user_id)

    async def list_async(
        self,
        *,
        request: Any = None,
    ) -> list[MockUser]:
        """Async version of list.

        Args:
            request: GetUserListRequest with filter parameters.

        Returns:
            List of MockUser objects matching the Clerk SDK's return type.
        """

        email_address = getattr(request, "email_address", None) if request else None
        phone_number = getattr(request, "phone_number", None) if request else None
        external_id = getattr(request, "external_id", None) if request else None
        username = getattr(request, "username", None) if request else None
        user_id = getattr(request, "user_id", None) if request else None
        query = getattr(request, "query", None) if request else None
        last_active_at_since = (
            getattr(request, "last_active_at_since", None) if request else None
        )
        limit = getattr(request, "limit", 10) if request else 10
        offset = getattr(request, "offset", 0) if request else 0
        order_by = (
            getattr(request, "order_by", "-created_at") if request else "-created_at"
        )

        return self.list(
            email_address=email_address,
            phone_number=phone_number,
            external_id=external_id,
            username=username,
            user_id=user_id,
            query=query,
            last_active_at_since=last_active_at_since,
            limit=limit,
            offset=offset,
            order_by=order_by,
        )

    async def update_async(
        self,
        *,
        user_id: str,
        external_id: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        username: str | None = None,
        password: str | None = None,
        primary_email_address_id: str | None = None,
        primary_phone_number_id: str | None = None,
        public_metadata: dict[str, Any] | None = None,
        private_metadata: dict[str, Any] | None = None,
        unsafe_metadata: dict[str, Any] | None = None,
        profile_image_id: str | None = None,
        skip_password_checks: bool = False,
        sign_out_of_other_sessions: bool = False,
        totp_secret: str | None = None,
        backup_codes: list[str] | None = None,
        delete_self_enabled: bool | None = None,
        create_organization_enabled: bool | None = None,
        notify_primary_email_address_changed: bool = False,
    ) -> MockUser:
        """Async version of update."""

        return self.update(
            user_id,
            external_id=external_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            password=password,
            primary_email_address_id=primary_email_address_id,
            primary_phone_number_id=primary_phone_number_id,
            public_metadata=public_metadata,
            private_metadata=private_metadata,
            unsafe_metadata=unsafe_metadata,
            profile_image_id=profile_image_id,
            skip_password_checks=skip_password_checks,
            sign_out_of_other_sessions=sign_out_of_other_sessions,
            totp_secret=totp_secret,
            backup_codes=backup_codes,
            delete_self_enabled=delete_self_enabled,
            create_organization_enabled=create_organization_enabled,
            notify_primary_email_address_changed=notify_primary_email_address_changed,
        )

    async def delete_async(self, *, user_id: str) -> MockUser:
        """Async version of delete."""

        return self.delete(user_id)

    async def count_async(
        self,
        *,
        email_address: list[str] | None = None,
        phone_number: list[str] | None = None,
        external_id: list[str] | None = None,
        username: list[str] | None = None,
        user_id: list[str] | None = None,
        query: str | None = None,
    ) -> int:
        """Async version of count."""

        return self.count(
            email_address=email_address,
            phone_number=phone_number,
            external_id=external_id,
            username=username,
            user_id=user_id,
            query=query,
        )
