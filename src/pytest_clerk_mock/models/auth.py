from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MockClerkUser(Enum):
    """Predefined user types for common test scenarios."""

    TEAM_OWNER = "user_test_owner"
    TEAM_MEMBER = "user_test_member"
    GUEST = "user_test_guest"
    UNAUTHENTICATED = None


class MockAuthResult(BaseModel):
    """Mock result from Clerk authenticate_request."""

    is_signed_in: bool = False
    payload: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_authenticated(self) -> bool:
        """Alias for is_signed_in."""

        return self.is_signed_in

    @classmethod
    def signed_in(
        cls,
        user_id: str,
        org_id: str | None = None,
        org_role: str = "org:admin",
    ) -> "MockAuthResult":
        """Create a signed-in auth result."""

        return cls(
            is_signed_in=True,
            payload={
                "sub": user_id,
                "org_id": org_id,
                "org_role": org_role,
            },
        )

    @classmethod
    def signed_out(cls) -> "MockAuthResult":
        """Create a signed-out auth result."""

        return cls(is_signed_in=False, payload={})
