from typing import Any

from pydantic import BaseModel, Field


class MockOrganization(BaseModel):
    """Represents a Clerk Organization."""

    object: str = "organization"
    id: str
    name: str = ""
    slug: str = ""
    image_url: str = ""
    has_image: bool = False
    created_by: str | None = None
    public_metadata: dict[str, Any] = Field(default_factory=dict)
    private_metadata: dict[str, Any] = Field(default_factory=dict)
    max_allowed_memberships: int = 0
    admin_delete_enabled: bool = False
    created_at: int = 0
    updated_at: int = 0
    members_count: int | None = None
    missing_member_with_elevated_permissions: bool | None = None
    pending_invitations_count: int | None = None
    last_active_at: int | None = None


class MockOrganizationMembership(BaseModel):
    """Represents a user's membership in an organization."""

    object: str = "organization_membership"
    id: str
    role: str = "org:member"
    role_name: str = ""
    permissions: list[str] = Field(default_factory=list)
    organization: MockOrganization | None = None
    organization_id: str | None = None
    user_id: str | None = None
    public_user_data: dict | None = None
    public_metadata: dict | None = None
    private_metadata: dict | None = None
    created_at: int = 0
    updated_at: int = 0


class MockOrganizationMembershipsResponse(BaseModel):
    """Response from get_organization_memberships_async."""

    data: list[MockOrganizationMembership] = Field(default_factory=list)
    total_count: int = 0
