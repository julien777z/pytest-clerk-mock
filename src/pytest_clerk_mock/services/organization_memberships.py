from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

import httpx
from clerk_backend_api import models, utils
from clerk_backend_api.models import ClerkErrors
from clerk_backend_api.types import UNSET, OptionalNullable

from pytest_clerk_mock.models.organization import (
    MockOrganizationMembership,
    MockOrganizationMembershipsResponse,
)
from pytest_clerk_mock.utils import build_http_response, create_clerk_error, generate_clerk_id

DEFAULT_LIST_LIMIT = 10
RESOURCE_NOT_FOUND_ERROR_CODE = "resource_not_found"
MEMBERSHIP_NOT_FOUND_RESPONSE_TEXT = "Organization membership not found."


def _create_membership_not_found_error(organization_id: str, user_id: str) -> ClerkErrors:
    """Create a ClerkErrors exception for missing memberships."""

    return create_clerk_error(
        status_code=404,
        response_text=MEMBERSHIP_NOT_FOUND_RESPONSE_TEXT,
        code=RESOURCE_NOT_FOUND_ERROR_CODE,
        message=f"Organization membership not found: {organization_id}:{user_id}",
    )


class MockOrganizationMembershipsClient:
    """Mock implementation of Clerk's OrganizationMemberships API."""

    def __init__(self) -> None:
        self._memberships: dict[str, MockOrganizationMembership] = {}

    def reset(self) -> None:
        """Clear all stored memberships."""

        self._memberships.clear()

    def _make_key(self, organization_id: str, user_id: str) -> str:
        """Create a unique key for a membership."""

        return f"{organization_id}:{user_id}"

    def create(
        self,
        *,
        organization_id: str,
        user_id: str,
        role: str,
        public_metadata: OptionalNullable[Dict[str, Any]] = UNSET,
        private_metadata: OptionalNullable[Dict[str, Any]] = UNSET,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.OrganizationMembership:
        """Create a new organization membership."""

        _ = retries, server_url, timeout_ms, http_headers
        key = self._make_key(organization_id, user_id)
        membership = MockOrganizationMembership(
            id=generate_clerk_id("orgmem"),
            organization_id=organization_id,
            user_id=user_id,
            role=role,
            public_metadata={} if public_metadata is UNSET else public_metadata,
            private_metadata={} if private_metadata is UNSET else private_metadata,
        )
        self._memberships[key] = membership

        return membership

    async def create_async(
        self,
        *,
        organization_id: str,
        user_id: str,
        role: str,
        public_metadata: OptionalNullable[Dict[str, Any]] = UNSET,
        private_metadata: OptionalNullable[Dict[str, Any]] = UNSET,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.OrganizationMembership:
        """Async version of create."""

        return self.create(
            organization_id=organization_id,
            user_id=user_id,
            role=role,
            public_metadata=public_metadata,
            private_metadata=private_metadata,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    def get(
        self,
        *,
        organization_id: str,
        user_id: str,
    ) -> MockOrganizationMembership | None:
        """Get a membership by organization and user ID."""

        key = self._make_key(organization_id, user_id)

        return self._memberships.get(key)

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

    def _public_user_data_str(
        self,
        membership: MockOrganizationMembership,
        key: str,
    ) -> str | None:
        """Return string-valued public_user_data field if present."""

        if not isinstance(membership.public_user_data, dict):
            return None

        value = membership.public_user_data.get(key)

        if isinstance(value, str):
            return value

        return None

    def _filter_by_exact_public_user_data(
        self,
        memberships: list[MockOrganizationMembership],
        *,
        key: str,
        values: list[str] | None,
        case_insensitive: bool = False,
    ) -> list[MockOrganizationMembership]:
        """Filter memberships by exact public user data values."""

        if not values:
            return memberships

        normalized_values = {value.lower() for value in values} if case_insensitive else set(values)
        filtered_memberships: list[MockOrganizationMembership] = []

        for membership in memberships:
            field_value = self._public_user_data_str(membership, key)
            if field_value is None:
                continue

            normalized_field_value = field_value.lower() if case_insensitive else field_value

            if normalized_field_value in normalized_values:
                filtered_memberships.append(membership)

        return filtered_memberships

    def _filter_by_partial_public_user_data(
        self,
        memberships: list[MockOrganizationMembership],
        *,
        key: str,
        query: str | None,
    ) -> list[MockOrganizationMembership]:
        """Filter memberships by case-insensitive partial public user data match."""

        if not query:
            return memberships

        normalized_query = query.lower()
        filtered_memberships: list[MockOrganizationMembership] = []

        for membership in memberships:
            field_value = self._public_user_data_str(membership, key)
            if field_value is None:
                continue

            if normalized_query in field_value.lower():
                filtered_memberships.append(membership)

        return filtered_memberships

    def _filter_by_name_query(
        self,
        memberships: list[MockOrganizationMembership],
        *,
        name_query: str | None,
    ) -> list[MockOrganizationMembership]:
        """Filter memberships by first or last name partial match."""

        if not name_query:
            return memberships

        normalized_query = name_query.lower()
        filtered_memberships: list[MockOrganizationMembership] = []

        for membership in memberships:
            first_name = self._public_user_data_str(
                membership,
                "first_name",
            )
            last_name = self._public_user_data_str(
                membership,
                "last_name",
            )
            first_name_matches = first_name is not None and normalized_query in first_name.lower()
            last_name_matches = last_name is not None and normalized_query in last_name.lower()

            if first_name_matches or last_name_matches:
                filtered_memberships.append(membership)

        return filtered_memberships

    def _filter_by_user_ids(
        self,
        memberships: list[MockOrganizationMembership],
        *,
        user_ids: list[str] | None,
    ) -> list[MockOrganizationMembership]:
        """Filter memberships by Clerk include/exclude user_id semantics."""

        if not user_ids:
            return memberships

        include_user_ids = {
            membership_user_id[1:] for membership_user_id in user_ids if membership_user_id.startswith("+")
        }
        exclude_user_ids = {
            membership_user_id[1:] for membership_user_id in user_ids if membership_user_id.startswith("-")
        }
        exact_user_ids = {
            membership_user_id
            for membership_user_id in user_ids
            if not membership_user_id.startswith("+") and not membership_user_id.startswith("-")
        }
        filtered_memberships = memberships

        if include_user_ids or exact_user_ids:
            allowed_user_ids = include_user_ids | exact_user_ids
            filtered_memberships = [
                membership for membership in filtered_memberships if membership.user_id in allowed_user_ids
            ]

        return [
            membership for membership in filtered_memberships if membership.user_id not in exclude_user_ids
        ]

    def _apply_ordering(
        self,
        memberships: list[MockOrganizationMembership],
        *,
        order_by: str | None,
    ) -> None:
        """Sort memberships in place using Clerk-like order_by values."""

        if not order_by:
            return

        reverse = order_by.startswith("-")
        sort_key = order_by.lstrip("-+")

        if sort_key == "created_at":
            memberships.sort(
                key=lambda membership: membership.created_at,
                reverse=reverse,
            )

            return

        public_user_data_key = {
            "email_address": "identifier",
            "phone_number": "phone_number",
            "username": "username",
            "first_name": "first_name",
            "last_name": "last_name",
        }.get(sort_key)
        if public_user_data_key is None:
            return

        memberships.sort(
            key=lambda membership: (
                self._public_user_data_str(membership, public_user_data_key) or ""
            ).lower(),
            reverse=reverse,
        )

    def list(
        self,
        *,
        organization_id: str,
        order_by: str | None = None,
        user_id: List[str] | None = None,
        email_address: List[str] | None = None,
        phone_number: List[str] | None = None,
        username: List[str] | None = None,
        web3_wallet: List[str] | None = None,
        role: List[str] | None = None,
        query: str | None = None,
        email_address_query: str | None = None,
        phone_number_query: str | None = None,
        username_query: str | None = None,
        name_query: str | None = None,
        last_active_at_before: int | None = None,
        last_active_at_after: int | None = None,
        created_at_before: int | None = None,
        created_at_after: int | None = None,
        limit: int | None = DEFAULT_LIST_LIMIT,
        offset: int | None = 0,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.OrganizationMemberships:
        """List memberships with Clerk-compatible filter parameters."""

        _ = retries, server_url, timeout_ms, http_headers
        memberships: list[MockOrganizationMembership] = [
            membership
            for membership in self._memberships.values()
            if membership.organization_id == organization_id
        ]
        memberships = self._filter_by_user_ids(memberships, user_ids=user_id)

        if role:
            role_set = set(role)
            memberships = [membership for membership in memberships if membership.role in role_set]

        if query:
            query_lower = query.lower()
            memberships = [
                membership
                for membership in memberships
                if query_lower in (membership.user_id or "").lower()
                or query_lower in membership.role.lower()
                or query_lower in (membership.organization_id or "").lower()
            ]

        for key, values, case_insensitive in (
            ("identifier", email_address, True),
            ("phone_number", phone_number, False),
            ("username", username, True),
            ("web3_wallet", web3_wallet, True),
        ):
            memberships = self._filter_by_exact_public_user_data(
                memberships,
                key=key,
                values=values,
                case_insensitive=case_insensitive,
            )
        for key, query_value in (
            ("identifier", email_address_query),
            ("phone_number", phone_number_query),
            ("username", username_query),
        ):
            memberships = self._filter_by_partial_public_user_data(
                memberships,
                key=key,
                query=query_value,
            )
        memberships = self._filter_by_name_query(
            memberships,
            name_query=name_query,
        )

        if last_active_at_before is not None:
            memberships = [
                membership for membership in memberships if membership.updated_at < last_active_at_before
            ]

        if last_active_at_after is not None:
            memberships = [
                membership for membership in memberships if membership.updated_at > last_active_at_after
            ]

        if created_at_before is not None:
            memberships = [
                membership for membership in memberships if membership.created_at < created_at_before
            ]

        if created_at_after is not None:
            memberships = [
                membership for membership in memberships if membership.created_at > created_at_after
            ]

        self._apply_ordering(memberships, order_by=order_by)

        total_count = len(memberships)
        normalized_offset = offset or 0
        normalized_limit = limit or DEFAULT_LIST_LIMIT
        memberships = memberships[normalized_offset : normalized_offset + normalized_limit]

        return MockOrganizationMembershipsResponse(
            data=memberships,
            total_count=total_count,
        )

    async def list_async(
        self,
        *,
        organization_id: str,
        order_by: str | None = None,
        user_id: List[str] | None = None,
        email_address: List[str] | None = None,
        phone_number: List[str] | None = None,
        username: List[str] | None = None,
        web3_wallet: List[str] | None = None,
        role: List[str] | None = None,
        query: str | None = None,
        email_address_query: str | None = None,
        phone_number_query: str | None = None,
        username_query: str | None = None,
        name_query: str | None = None,
        last_active_at_before: int | None = None,
        last_active_at_after: int | None = None,
        created_at_before: int | None = None,
        created_at_after: int | None = None,
        limit: int | None = DEFAULT_LIST_LIMIT,
        offset: int | None = 0,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.OrganizationMemberships:
        """Async version of list."""

        _ = retries, server_url, timeout_ms, http_headers

        return self.list(
            organization_id=organization_id,
            order_by=order_by,
            user_id=user_id,
            email_address=email_address,
            phone_number=phone_number,
            username=username,
            web3_wallet=web3_wallet,
            role=role,
            query=query,
            email_address_query=email_address_query,
            phone_number_query=phone_number_query,
            username_query=username_query,
            name_query=name_query,
            last_active_at_before=last_active_at_before,
            last_active_at_after=last_active_at_after,
            created_at_before=created_at_before,
            created_at_after=created_at_after,
            limit=limit,
            offset=offset,
        )

    def update(
        self,
        *,
        organization_id: str,
        user_id: str,
        role: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.OrganizationMembership:
        """Update a membership role."""

        _ = retries, server_url, timeout_ms, http_headers
        key = self._make_key(organization_id, user_id)
        if key not in self._memberships:
            raise _create_membership_not_found_error(organization_id, user_id)

        membership = self._memberships[key]
        updated_membership = membership.model_copy(update={"role": role})
        self._memberships[key] = updated_membership

        return updated_membership

    def update_metadata(
        self,
        *,
        organization_id: str,
        user_id: str,
        public_metadata: Dict[str, Any] | None = None,
        private_metadata: Dict[str, Any] | None = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.OrganizationMembership:
        """Merge metadata into a membership."""

        _ = retries, server_url, timeout_ms, http_headers
        key = self._make_key(organization_id, user_id)
        if key not in self._memberships:
            raise _create_membership_not_found_error(organization_id, user_id)

        membership = self._memberships[key]
        updated_membership = membership.model_copy(
            update={
                "public_metadata": {**(membership.public_metadata or {}), **(public_metadata or {})},
                "private_metadata": {
                    **(membership.private_metadata or {}),
                    **(private_metadata or {}),
                },
            }
        )
        self._memberships[key] = updated_membership

        return updated_membership

    async def update_async(
        self,
        *,
        organization_id: str,
        user_id: str,
        role: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.OrganizationMembership:
        """Async version of update."""

        return self.update(
            organization_id=organization_id,
            user_id=user_id,
            role=role,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def update_metadata_async(
        self,
        *,
        organization_id: str,
        user_id: str,
        public_metadata: Dict[str, Any] | None = None,
        private_metadata: Dict[str, Any] | None = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.OrganizationMembership:
        """Async version of update_metadata."""

        return self.update_metadata(
            organization_id=organization_id,
            user_id=user_id,
            public_metadata=public_metadata,
            private_metadata=private_metadata,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    def delete(
        self,
        *,
        organization_id: str,
        user_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.OrganizationMembership:
        """Delete a membership."""

        _ = retries, server_url, timeout_ms, http_headers
        key = self._make_key(organization_id, user_id)
        if key not in self._memberships:
            raise _create_membership_not_found_error(organization_id, user_id)

        return self._memberships.pop(key)

    async def delete_async(
        self,
        *,
        organization_id: str,
        user_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.OrganizationMembership:
        """Async version of delete."""

        return self.delete(
            organization_id=organization_id,
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
