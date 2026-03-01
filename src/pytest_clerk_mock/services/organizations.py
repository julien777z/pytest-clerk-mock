from http import HTTPStatus
from typing import Final

from pytest_clerk_mock.helpers import create_clerk_error
from pytest_clerk_mock.models.organization import MockOrganization

RESOURCE_NOT_FOUND_ERROR_CODE: Final[str] = "resource_not_found"
ORGANIZATION_NOT_FOUND_RESPONSE_TEXT: Final[str] = "Organization not found."


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
