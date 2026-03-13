from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from http import HTTPStatus
from typing import Final, TypeVar

from clerk_backend_api import utils
from clerk_backend_api.types import UNSET, OptionalNullable

from pytest_clerk_mock.helpers import create_clerk_error, generate_clerk_id
from pytest_clerk_mock.interfaces.organization_requests import (
    CreateOrganizationRequestBody,
    MetadataDict,
)
from pytest_clerk_mock.models.organization import MockOrganization

RESOURCE_NOT_FOUND_ERROR_CODE: Final[str] = "resource_not_found"
ORGANIZATION_NOT_FOUND_RESPONSE_TEXT: Final[str] = "Organization not found."
DEFAULT_MAX_ALLOWED_MEMBERSHIPS: Final[int] = 0

RequestValueT = TypeVar("RequestValueT")


def _resolve_optional_nullable(
    value: OptionalNullable[RequestValueT],
) -> RequestValueT | None:
    """Resolve Clerk optional-nullable values into plain Python values."""

    if value is UNSET:
        return None

    return value


def _resolve_metadata(
    metadata: OptionalNullable[MetadataDict] | None,
) -> dict[str, object] | None:
    """Convert request metadata into stored dict values."""

    resolved_metadata = _resolve_optional_nullable(metadata) if metadata is not None else None
    if resolved_metadata is None:
        return None

    return dict(resolved_metadata)


def _resolve_created_at(created_at: OptionalNullable[str]) -> int | None:
    """Convert Clerk created_at strings into epoch milliseconds."""

    resolved_created_at = _resolve_optional_nullable(created_at)
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
        request: CreateOrganizationRequestBody | None = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> MockOrganization:
        """Create a new organization using Clerk-style request payloads."""

        _ = retries, server_url, timeout_ms, http_headers

        request_payload: CreateOrganizationRequestBody = request or {"name": ""}
        resolved_name = request_payload["name"]
        resolved_created_by = _resolve_optional_nullable(request_payload.get("created_by", UNSET))
        resolved_slug = _resolve_optional_nullable(request_payload.get("slug", UNSET)) or ""
        resolved_public_metadata = _resolve_metadata(request_payload.get("public_metadata", UNSET))
        resolved_private_metadata = _resolve_metadata(request_payload.get("private_metadata", UNSET))
        resolved_created_at = _resolve_created_at(request_payload.get("created_at", UNSET))
        resolved_max_allowed_memberships = _resolve_optional_nullable(
            request_payload.get("max_allowed_memberships", UNSET)
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

    def get(self, organization_id: str) -> MockOrganization:
        """Get an organization by ID."""

        if organization_id not in self._organizations:
            raise create_clerk_error(
                status_code=HTTPStatus.NOT_FOUND,
                code=RESOURCE_NOT_FOUND_ERROR_CODE,
                message=f"Organization not found: {organization_id}",
                response_text=ORGANIZATION_NOT_FOUND_RESPONSE_TEXT,
            )

        return self._organizations[organization_id]

    async def get_async(self, organization_id: str) -> MockOrganization:
        """Async version of get."""

        return self.get(organization_id)

    async def create_async(
        self,
        *,
        request: CreateOrganizationRequestBody | None = None,
        retries: OptionalNullable[utils.RetryConfig] = UNSET,
        server_url: str | None = None,
        timeout_ms: int | None = None,
        http_headers: Mapping[str, str] | None = None,
    ) -> MockOrganization:
        """Async version of create."""

        return self.create(
            request=request,
            retries=retries,
            server_url=server_url,
            timeout_ms=timeout_ms,
            http_headers=http_headers,
        )
