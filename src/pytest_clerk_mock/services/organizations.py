from __future__ import annotations

from datetime import datetime
from http import HTTPStatus
from typing import Any, Dict, Final, List, Mapping, Tuple

import httpx
from clerk_backend_api import models, utils
from clerk_backend_api.types import UNSET, OptionalNullable

from pytest_clerk_mock.interfaces.organization_requests import MetadataDict
from pytest_clerk_mock.models.commerce import MockCommerceSubscription
from pytest_clerk_mock.models.organization import MockOrganization
from pytest_clerk_mock.utils import (
    build_commerce_subscription,
    build_http_response,
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


def _build_organization_with_logo(
    organization: MockOrganization,
    *,
    image_url: str,
) -> models.OrganizationWithLogo:
    """Build an OrganizationWithLogo payload from a stored mock organization."""

    return models.OrganizationWithLogo.model_validate(
        {
            "object": "organization",
            "id": organization.id,
            "name": organization.name,
            "slug": organization.slug,
            "image_url": image_url,
            "has_image": bool(image_url),
            "max_allowed_memberships": organization.max_allowed_memberships,
            "admin_delete_enabled": False,
            "public_metadata": organization.public_metadata,
            "created_at": organization.created_at,
            "updated_at": organization.updated_at,
            "private_metadata": organization.private_metadata,
            "created_by": organization.created_by,
            "last_active_at": 0,
            "logo_url": image_url or None,
        }
    )


class MockOrganizationsClient:
    """Mock implementation of Clerk's Organizations API."""

    def __init__(self) -> None:
        self._organizations: dict[str, MockOrganization] = {}

    def reset(self) -> None:
        """Clear all stored organizations."""

        self._organizations.clear()

    def _get_organization_or_error(self, organization_id: str) -> MockOrganization:
        """Return a stored organization or raise the Clerk not-found error."""

        if organization_id not in self._organizations:
            raise create_clerk_error(
                status_code=HTTPStatus.NOT_FOUND,
                code=RESOURCE_NOT_FOUND_ERROR_CODE,
                message=f"Organization not found: {organization_id}",
                response_text=ORGANIZATION_NOT_FOUND_RESPONSE_TEXT,
            )

        return self._organizations[organization_id]

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
        request: (
            models.CreateOrganizationRequestBody | models.CreateOrganizationRequestBodyTypedDict | None
        ) = None,
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
        return self._get_organization_or_error(organization_id)

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

    def delete_logo(
        self,
        *,
        organization_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.Organization:
        """Delete an organization's logo."""

        _ = retries, server_url, timeout_ms, http_headers

        organization = self._get_organization_or_error(organization_id)
        updated_organization = organization.model_copy(update={"image_url": "", "has_image": False})
        self._organizations[organization_id] = updated_organization

        return updated_organization

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
        organization_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> MockCommerceSubscription:
        """Return a placeholder billing subscription for an organization."""

        _ = retries, server_url, timeout_ms, http_headers
        self._get_organization_or_error(organization_id)

        return build_commerce_subscription(payer_id=organization_id)

    def merge_metadata(
        self,
        *,
        organization_id: str,
        public_metadata: Dict[str, Any] | None = None,
        private_metadata: Dict[str, Any] | None = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.Organization:
        """Merge metadata into an organization."""

        _ = retries, server_url, timeout_ms, http_headers
        organization = self._get_organization_or_error(organization_id)

        return self.update(
            organization_id=organization_id,
            public_metadata={**organization.public_metadata, **(public_metadata or {})},
            private_metadata={**organization.private_metadata, **(private_metadata or {})},
        )

    def upload_logo(
        self,
        *,
        organization_id: str,
        file: models.UploadOrganizationLogoFile | models.UploadOrganizationLogoFileTypedDict,
        uploader_user_id: str | None = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.OrganizationWithLogo:
        """Return an OrganizationWithLogo payload for the uploaded logo."""

        _ = uploader_user_id, retries, server_url, timeout_ms, http_headers
        organization = self._get_organization_or_error(organization_id)
        image_name = get_request_value(file, "name") or "organization-logo"
        image_url = f"https://img.clerk.mock/{organization_id}/{image_name}"
        self._organizations[organization_id] = organization.model_copy(
            update={"image_url": image_url, "has_image": True}
        )
        organization = self._organizations[organization_id]

        return _build_organization_with_logo(organization, image_url=image_url)

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
        request: (
            models.CreateOrganizationRequestBody | models.CreateOrganizationRequestBodyTypedDict | None
        ) = None,
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

    async def delete_logo_async(
        self,
        *,
        organization_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.Organization:
        """Async version of delete_logo."""

        return self.delete_logo(
            organization_id=organization_id,
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
        organization_id: str,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> MockCommerceSubscription:
        """Async version of get_billing_subscription."""

        return self.get_billing_subscription(
            organization_id=organization_id,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def merge_metadata_async(
        self,
        *,
        organization_id: str,
        public_metadata: Dict[str, Any] | None = None,
        private_metadata: Dict[str, Any] | None = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.Organization:
        """Async version of merge_metadata."""

        return self.merge_metadata(
            organization_id=organization_id,
            public_metadata=public_metadata,
            private_metadata=private_metadata,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )

    async def upload_logo_async(
        self,
        *,
        organization_id: str,
        file: models.UploadOrganizationLogoFile | models.UploadOrganizationLogoFileTypedDict,
        uploader_user_id: str | None = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> models.OrganizationWithLogo:
        """Async version of upload_logo."""

        return self.upload_logo(
            organization_id=organization_id,
            file=file,
            uploader_user_id=uploader_user_id,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )
