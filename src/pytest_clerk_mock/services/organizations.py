from __future__ import annotations

from datetime import datetime
from http import HTTPStatus
from typing import Any, Dict, Final, List, Mapping

from clerk_backend_api import models, utils
from clerk_backend_api.types import UNSET, OptionalNullable

from pytest_clerk_mock.interfaces.organization_requests import MetadataDict
from pytest_clerk_mock.models.organization import MockOrganization
from pytest_clerk_mock.utils import (
    create_clerk_error,
    generate_clerk_id,
    get_request_value,
    resolve_optional_nullable,
)

RESOURCE_NOT_FOUND_ERROR_CODE: Final[str] = "resource_not_found"
ORGANIZATION_NOT_FOUND_RESPONSE_TEXT: Final[str] = "Organization not found."
DEFAULT_MAX_ALLOWED_MEMBERSHIPS: Final[int] = 0

def _resolve_metadata(
    metadata: OptionalNullable[MetadataDict] | None,
) -> dict[str, object] | None:
    """Convert request metadata into stored dict values."""

    resolved_metadata = resolve_optional_nullable(metadata) if metadata is not None else None
    if resolved_metadata is None:
        return None

    return dict(resolved_metadata)


def _resolve_created_at(created_at: OptionalNullable[str]) -> int | None:
    """Convert Clerk created_at strings into epoch milliseconds."""

    resolved_created_at = resolve_optional_nullable(created_at)
    if resolved_created_at is None:
        return None

    normalized_created_at = resolved_created_at.replace("Z", "+00:00")

    return int(datetime.fromisoformat(normalized_created_at).timestamp() * 1000)


class MockOrganizationsClient:
    """Mock implementation of Clerk's Organizations API."""

    def __init__(self) -> None:
        self._organizations: dict[str, MockOrganization] = {}

    def reset(self) -> None:
        """Clear all stored organizations."""

        self._organizations.clear()

    def add(
        self,
        org_id: str,
        name: str = "",
        slug: str = "",
    ) -> MockOrganization:
        """Register a mock organization."""

        org = self._store_organization(
            org_id=org_id,
            name=name,
            slug=slug,
        )

        return org

    def _store_organization(
        self,
        *,
        org_id: str,
        name: str = "",
        slug: str = "",
        created_by: str | None = None,
        public_metadata: dict[str, object] | None = None,
        private_metadata: dict[str, object] | None = None,
        max_allowed_memberships: int = DEFAULT_MAX_ALLOWED_MEMBERSHIPS,
        created_at: int | None = None,
    ) -> MockOrganization:
        """Persist a mock organization."""

        org = MockOrganization(
            id=org_id,
            name=name,
            slug=slug,
            created_by=created_by,
            public_metadata=public_metadata or {},
            private_metadata=private_metadata or {},
            max_allowed_memberships=max_allowed_memberships,
            created_at=created_at if created_at is not None else 0,
        )
        self._organizations[org_id] = org

        return org

    def create(
        self,
        *,
        request: models.CreateOrganizationRequestBody | dict[str, Any] | None = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.Organization:
        """Create a new organization using Clerk-style request payloads."""

        _ = retries, server_url, timeout_ms, http_headers

        request_payload = request or {"name": ""}
        resolved_name = get_request_value(request_payload, "name")
        resolved_created_by = resolve_optional_nullable(
            get_request_value(request_payload, "created_by", UNSET)
        )
        resolved_slug = (
            resolve_optional_nullable(get_request_value(request_payload, "slug", UNSET)) or ""
        )
        resolved_public_metadata = _resolve_metadata(
            get_request_value(request_payload, "public_metadata", UNSET)
        )
        resolved_private_metadata = _resolve_metadata(
            get_request_value(request_payload, "private_metadata", UNSET)
        )
        resolved_created_at = _resolve_created_at(
            get_request_value(request_payload, "created_at", UNSET)
        )
        resolved_max_allowed_memberships = resolve_optional_nullable(
            get_request_value(request_payload, "max_allowed_memberships", UNSET)
        )

        return self._store_organization(
            org_id=generate_clerk_id("org"),
            name=resolved_name,
            slug=resolved_slug,
            created_by=resolved_created_by,
            public_metadata=resolved_public_metadata,
            private_metadata=resolved_private_metadata,
            max_allowed_memberships=(
                resolved_max_allowed_memberships
                if resolved_max_allowed_memberships is not None
                else DEFAULT_MAX_ALLOWED_MEMBERSHIPS
            ),
            created_at=resolved_created_at,
        )

    def get(
        self,
        *,
        organization_id: str,
        include_members_count: bool | None = None,
        include_missing_member_with_elevated_permissions: bool | None = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.Organization:
        """Get an organization by ID."""

        _ = (
            include_members_count,
            include_missing_member_with_elevated_permissions,
            retries,
            server_url,
            timeout_ms,
            http_headers,
        )
        if organization_id not in self._organizations:
            raise create_clerk_error(
                status_code=HTTPStatus.NOT_FOUND,
                code=RESOURCE_NOT_FOUND_ERROR_CODE,
                message=f"Organization not found: {organization_id}",
                response_text=ORGANIZATION_NOT_FOUND_RESPONSE_TEXT,
            )

        return self._organizations[organization_id]

    def list(
        self,
        *,
        include_members_count: bool | None = None,
        include_missing_member_with_elevated_permissions: bool | None = None,
        query: str | None = None,
        user_id: List[str] | None = None,
        organization_id: List[str] | None = None,
        order_by: str | None = "-created_at",
        limit: int | None = 10,
        offset: int | None = 0,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.Organizations:
        """List organizations with Clerk-style filters."""

        _ = (
            include_members_count,
            include_missing_member_with_elevated_permissions,
            user_id,
            retries,
            server_url,
            timeout_ms,
            http_headers,
        )
        organizations = list(self._organizations.values())

        if query:
            query_lower = query.lower()
            organizations = [
                organization
                for organization in organizations
                if query_lower in organization.name.lower()
                or query_lower in organization.slug.lower()
                or query_lower in organization.id.lower()
            ]

        if organization_id:
            organization_id_set = set(organization_id)
            organizations = [
                organization for organization in organizations if organization.id in organization_id_set
            ]

        resolved_order_by = order_by or "-created_at"
        reverse = resolved_order_by.startswith("-")
        sort_key = resolved_order_by.lstrip("-+")

        if sort_key == "created_at":
            organizations.sort(key=lambda organization: organization.created_at, reverse=reverse)
        elif sort_key == "updated_at":
            organizations.sort(key=lambda organization: organization.updated_at, reverse=reverse)
        elif sort_key == "name":
            organizations.sort(key=lambda organization: organization.name.lower(), reverse=reverse)

        total_count = len(organizations)
        resolved_offset = offset or 0
        resolved_limit = limit or 10
        organizations = organizations[resolved_offset : resolved_offset + resolved_limit]

        return models.Organizations(data=organizations, total_count=total_count)

    def update(
        self,
        *,
        organization_id: str,
        public_metadata: OptionalNullable[Dict[str, Any]] = UNSET,
        private_metadata: OptionalNullable[Dict[str, Any]] = UNSET,
        name: OptionalNullable[str] = UNSET,
        slug: OptionalNullable[str] = UNSET,
        max_allowed_memberships: OptionalNullable[int] = UNSET,
        admin_delete_enabled: OptionalNullable[bool] = UNSET,
        created_at: OptionalNullable[str] = UNSET,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.Organization:
        """Update an organization by ID."""

        _ = admin_delete_enabled, created_at, retries, server_url, timeout_ms, http_headers
        organization = self.get(
            organization_id=organization_id,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )
        update_data = {
            "public_metadata": _resolve_metadata(public_metadata),
            "private_metadata": _resolve_metadata(private_metadata),
            "name": resolve_optional_nullable(name),
            "slug": resolve_optional_nullable(slug),
            "max_allowed_memberships": resolve_optional_nullable(max_allowed_memberships),
        }
        update_data = {key: value for key, value in update_data.items() if value is not None}
        updated_organization = organization.model_copy(update=update_data)
        self._organizations[organization_id] = updated_organization

        return updated_organization

    def delete(
        self,
        *,
        organization_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.DeletedObject:
        """Delete an organization by ID."""

        _ = retries, server_url, timeout_ms, http_headers
        organization = self.get(
            organization_id=organization_id,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )
        self._organizations.pop(organization_id)

        return models.DeletedObject(
            object="organization",
            deleted=True,
            id=organization.id,
            slug=organization.slug,
        )

    async def get_async(
        self,
        *,
        organization_id: str,
        include_members_count: bool | None = None,
        include_missing_member_with_elevated_permissions: bool | None = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.Organization:
        """Async version of get."""

        return self.get(
            organization_id=organization_id,
            include_members_count=include_members_count,
            include_missing_member_with_elevated_permissions=(
                include_missing_member_with_elevated_permissions
            ),
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def list_async(
        self,
        *,
        include_members_count: bool | None = None,
        include_missing_member_with_elevated_permissions: bool | None = None,
        query: str | None = None,
        user_id: List[str] | None = None,
        organization_id: List[str] | None = None,
        order_by: str | None = "-created_at",
        limit: int | None = 10,
        offset: int | None = 0,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.Organizations:
        """Async version of list."""

        return self.list(
            include_members_count=include_members_count,
            include_missing_member_with_elevated_permissions=(
                include_missing_member_with_elevated_permissions
            ),
            query=query,
            user_id=user_id,
            organization_id=organization_id,
            order_by=order_by,
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
        request: models.CreateOrganizationRequestBody | dict[str, Any] | None = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.Organization:
        """Async version of create."""

        return self.create(
            request=request,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def update_async(
        self,
        *,
        organization_id: str,
        public_metadata: OptionalNullable[Dict[str, Any]] = UNSET,
        private_metadata: OptionalNullable[Dict[str, Any]] = UNSET,
        name: OptionalNullable[str] = UNSET,
        slug: OptionalNullable[str] = UNSET,
        max_allowed_memberships: OptionalNullable[int] = UNSET,
        admin_delete_enabled: OptionalNullable[bool] = UNSET,
        created_at: OptionalNullable[str] = UNSET,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.Organization:
        """Async version of update."""

        return self.update(
            organization_id=organization_id,
            public_metadata=public_metadata,
            private_metadata=private_metadata,
            name=name,
            slug=slug,
            max_allowed_memberships=max_allowed_memberships,
            admin_delete_enabled=admin_delete_enabled,
            created_at=created_at,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def delete_async(
        self,
        *,
        organization_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.DeletedObject:
        """Async version of delete."""

        return self.delete(
            organization_id=organization_id,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )
