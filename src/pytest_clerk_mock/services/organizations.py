from pytest_clerk_mock.models.organization import MockOrganization


class OrganizationNotFoundError(Exception):
    """Raised when an organization is not found."""

    def __init__(self, organization_id: str) -> None:
        self.organization_id = organization_id
        super().__init__(f"Organization not found: {organization_id}")


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

        org = MockOrganization(id=org_id, name=name, slug=slug)
        self._organizations[org_id] = org

        return org

    def get(self, organization_id: str) -> MockOrganization:
        """Get an organization by ID."""

        if organization_id not in self._organizations:
            raise OrganizationNotFoundError(organization_id)

        return self._organizations[organization_id]

    async def get_async(self, organization_id: str) -> MockOrganization:
        """Async version of get."""

        return self.get(organization_id)
