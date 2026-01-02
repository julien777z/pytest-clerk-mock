from contextlib import contextmanager
from typing import Generator
from unittest.mock import MagicMock, patch

import httpx
from clerk_backend_api import SDKError
from clerk_backend_api.models import ClerkErrors
from clerk_backend_api.models.clerkerror import ClerkError
from clerk_backend_api.models.clerkerrors import ClerkErrorsData
from pydantic import BaseModel

EMAIL_EXISTS_ERROR_CODE = "form_identifier_exists"


class MockClerkUserResponse(BaseModel):
    """Simple mock Clerk user returned from create_async."""

    id: str


class MockClerkUserListResponse:
    """Mock response from Clerk users.list_async."""

    def __init__(self, data: list[MockClerkUserResponse]):
        self.data = data

    def __getitem__(self, index: int) -> MockClerkUserResponse:
        return self.data[index]

    def __len__(self) -> int:
        return len(self.data)

    def __bool__(self) -> bool:
        return len(self.data) > 0


def create_clerk_errors(data: object | None = None) -> ClerkErrors:
    """Create a ClerkErrors exception for testing.

    Args:
        data: The data payload for the error (can be None, ClerkErrorsData, or MagicMock).

    Returns:
        A ClerkErrors exception ready to be used as side_effect.
    """

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 400
    mock_response.text = "Mock error"
    mock_response.headers = httpx.Headers({})

    return ClerkErrors(data=data, raw_response=mock_response, body="Mock error")


@contextmanager
def mock_clerk_user_creation(
    patch_target: str,
    clerk_user_id: str = "user_clerk_mock_123",
) -> Generator[MagicMock, None, None]:
    """Mock Clerk user creation API.

    Args:
        patch_target: The module path to patch.
        clerk_user_id: The ID to return for the created user.

    Yields:
        The mock object for assertions.

    Example:
        with mock_clerk_user_creation("api.core.clerk.clerk.users.create_async", "user_123") as mock:
            # Your test code here
            mock.assert_called_once()
    """

    with patch(patch_target) as mock_create:
        mock_create.return_value = MockClerkUserResponse(id=clerk_user_id)
        yield mock_create


@contextmanager
def mock_clerk_user_creation_failure(
    patch_target: str,
    error_message: str = "Clerk API error",
) -> Generator[MagicMock, None, None]:
    """Mock Clerk user creation API to simulate a failure.

    Args:
        patch_target: The module path to patch.
        error_message: The error message to include.

    Yields:
        The mock object for assertions.

    Example:
        with mock_clerk_user_creation_failure("api.core.clerk.clerk.users.create_async") as mock:
            with pytest.raises(ErrorResponse):
                # Your test code here
    """

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = error_message
    mock_response.headers = {}

    with patch(patch_target) as mock_create:
        mock_create.side_effect = SDKError(error_message, mock_response)
        yield mock_create


@contextmanager
def mock_clerk_user_exists(
    create_patch_target: str,
    list_patch_target: str,
    existing_clerk_user_id: str = "user_clerk_existing_123",
) -> Generator[tuple[MagicMock, MagicMock], None, None]:
    """Mock Clerk user creation to simulate an email already exists scenario.

    This simulates the case where create_async fails because the email is taken,
    but list_async returns the existing user so we can link it.

    Args:
        create_patch_target: The module path to patch for create_async.
        list_patch_target: The module path to patch for list_async.
        existing_clerk_user_id: The ID of the existing Clerk user to return.

    Yields:
        A tuple of (mock_create, mock_list) for assertions.

    Example:
        with mock_clerk_user_exists(
            "api.core.clerk.clerk.users.create_async",
            "api.core.clerk.clerk.users.list_async",
            "user_existing_123"
        ) as (mock_create, mock_list):
            # Your test code here
            mock_create.assert_called_once()
            mock_list.assert_called_once()
    """

    mock_response = httpx.Response(
        status_code=422,
        json={
            "errors": [
                {
                    "message": "That email address is taken. Please try another.",
                    "long_message": "That email address is taken. Please try another.",
                    "code": EMAIL_EXISTS_ERROR_CODE,
                }
            ]
        },
    )

    email_exists_error = ClerkErrors(
        data=ClerkErrorsData(
            errors=[
                ClerkError(
                    message="That email address is taken. Please try another.",
                    long_message="That email address is taken. Please try another.",
                    code=EMAIL_EXISTS_ERROR_CODE,
                )
            ]
        ),
        raw_response=mock_response,
    )

    with (
        patch(create_patch_target) as mock_create,
        patch(list_patch_target) as mock_list,
    ):
        mock_create.side_effect = email_exists_error
        mock_list.return_value = MockClerkUserListResponse(
            data=[MockClerkUserResponse(id=existing_clerk_user_id)]
        )
        yield mock_create, mock_list
