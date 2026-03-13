import secrets
from contextlib import contextmanager
from http import HTTPStatus
from typing import Any, Final, Generator, TypeVar
from unittest.mock import MagicMock, patch

import httpx
from clerk_backend_api import SDKError
from clerk_backend_api import models
from clerk_backend_api.models import ClerkErrors
from clerk_backend_api.models.clerkerror import ClerkError
from clerk_backend_api.models.clerkerrors import ClerkErrorsData
from clerk_backend_api.types import UNSET, OptionalNullable

from pytest_clerk_mock.models.user import MockClerkUserResponse

EMAIL_EXISTS_ERROR_CODE: Final[str] = "form_identifier_exists"
DEFAULT_ERROR_TEXT: Final[str] = "Mock error"
DEFAULT_ERROR_CODE: Final[str] = "mock_error"

RequestValueT = TypeVar("RequestValueT")


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


def generate_clerk_id(prefix: str | None = None) -> str:
    """Generate a random Clerk-style identifier."""

    identifier = secrets.token_hex(12)

    if prefix is None:
        return identifier

    return f"{prefix}_{identifier}"


def create_clerk_error(
    *,
    status_code: HTTPStatus,
    code: str,
    message: str,
    response_text: str,
    body: str | None = None,
) -> ClerkErrors:
    """Create a ClerkErrors exception with one error payload."""

    response = httpx.Response(status_code=status_code, text=response_text)

    return ClerkErrors(
        data=ClerkErrorsData(
            errors=[
                ClerkError(
                    code=code,
                    message=message,
                    long_message=message,
                )
            ]
        ),
        raw_response=response,
        body=body or response_text,
    )


def create_clerk_errors(data: object | None = None) -> ClerkErrors:
    """Create a ClerkErrors exception for tests."""

    if data is not None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = HTTPStatus.BAD_REQUEST
        mock_response.text = DEFAULT_ERROR_TEXT
        mock_response.headers = httpx.Headers({})
        return ClerkErrors(data=data, raw_response=mock_response, body=DEFAULT_ERROR_TEXT)

    return create_clerk_error(
        status_code=HTTPStatus.BAD_REQUEST,
        code=DEFAULT_ERROR_CODE,
        message=DEFAULT_ERROR_TEXT,
        response_text=DEFAULT_ERROR_TEXT,
    )


def build_http_response() -> httpx.Response:
    """Build a generic successful HTTP response for low-level SDK hooks."""

    return httpx.Response(status_code=HTTPStatus.OK, json={})


def build_commerce_subscription(*, payer_id: str) -> models.CommerceSubscription:
    """Build a minimal CommerceSubscription payload."""

    return models.CommerceSubscription.model_validate(
        {
            "object": "commerce_subscription",
            "id": generate_clerk_id("sub"),
            "instance_id": generate_clerk_id("inst"),
            "status": "active",
            "payer_id": payer_id,
            "created_at": 0,
            "updated_at": 0,
            "active_at": 0,
            "past_due_at": None,
            "subscription_items": [
                {
                    "object": "commerce_subscription_item",
                    "id": generate_clerk_id("subitem"),
                    "instance_id": generate_clerk_id("inst"),
                    "status": "active",
                    "plan_id": None,
                    "plan_period": "month",
                    "payer_id": payer_id,
                    "is_free_trial": False,
                    "period_start": 0,
                    "period_end": None,
                    "canceled_at": None,
                    "past_due_at": None,
                    "ended_at": None,
                }
            ],
        }
    )


def resolve_optional_nullable(value: OptionalNullable[RequestValueT]) -> RequestValueT | None:
    """Resolve Clerk optional-nullable values into plain Python values."""

    if value is UNSET:
        return None

    return value


def get_request_value(request: object, key: str, default: Any = None) -> Any:
    """Read a field from either a Clerk request model or typed dict."""

    if isinstance(request, dict):
        return request.get(key, default)

    if hasattr(request, "model_dump"):
        return request.model_dump(mode="python").get(key, default)

    return getattr(request, key, default)


@contextmanager
def mock_clerk_user_creation(
    patch_target: str,
    clerk_user_id: str = "user_clerk_mock_123",
) -> Generator[MagicMock, None, None]:
    """Mock the Clerk user creation API."""

    with patch(patch_target) as mock_create:
        mock_create.return_value = MockClerkUserResponse(id=clerk_user_id)
        yield mock_create


@contextmanager
def mock_clerk_user_creation_failure(
    patch_target: str,
    error_message: str = "Clerk API error",
) -> Generator[MagicMock, None, None]:
    """Mock the Clerk user creation API to raise an SDK error."""

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
    """Mock Clerk user creation to simulate an existing-email conflict."""

    email_exists_error = create_clerk_error(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        code=EMAIL_EXISTS_ERROR_CODE,
        message="That email address is taken. Please try another.",
        response_text="That email address is taken.",
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
