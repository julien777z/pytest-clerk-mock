from pydantic import BaseModel, Field


class MockOrganization(BaseModel):
    """Represents a Clerk Organization."""

    id: str
    name: str = ""
    slug: str = ""
    created_at: int = 0
    updated_at: int = 0


class MockOrganizationMembership(BaseModel):
    """Represents a user's membership in an organization."""

    id: str
    role: str = "org:member"
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

