from typing import Any

from pydantic import BaseModel

from pytest_clerk_mock.models.auth import MockAuthResult


class AuthSnapshot(BaseModel):
    """Snapshot of authentication state for restoration."""

    user_id: str | None
    org_id: str | None
    org_role: str


class MockAuthState:
    """Manages authentication state for mock Clerk client."""

    def __init__(self) -> None:
        self._user_id: str | None = None
        self._org_id: str | None = None
        self._org_role: str = "org:admin"

    def configure(
        self,
        user_id: str | None,
        org_id: str | None = None,
        org_role: str = "org:admin",
    ) -> None:
        """Configure the authentication state."""

        self._user_id = user_id
        self._org_id = org_id
        self._org_role = org_role

    def get_result(self) -> MockAuthResult:
        """Get the current authentication result."""

        if self._user_id is None:
            return MockAuthResult.signed_out()

        return MockAuthResult.signed_in(
            user_id=self._user_id,
            org_id=self._org_id,
            org_role=self._org_role,
        )

    def snapshot(self) -> AuthSnapshot:
        """Take a snapshot of the current state."""

        return AuthSnapshot(
            user_id=self._user_id,
            org_id=self._org_id,
            org_role=self._org_role,
        )

    def restore(self, snapshot: AuthSnapshot) -> None:
        """Restore state from a snapshot."""

        self._user_id = snapshot.user_id
        self._org_id = snapshot.org_id
        self._org_role = snapshot.org_role

    def reset(self) -> None:
        """Reset authentication state to defaults."""

        self._user_id = None
        self._org_id = None
        self._org_role = "org:admin"

