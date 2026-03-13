import inspect
from typing import Any, Final, Protocol, get_type_hints

import pytest
from clerk_backend_api import models
from clerk_backend_api.organizationmemberships_sdk import OrganizationMembershipsSDK
from clerk_backend_api.organizations_sdk import OrganizationsSDK
from clerk_backend_api.users import Users

import pytest_clerk_mock.interfaces.organization_requests as organization_request_interfaces
import pytest_clerk_mock.interfaces.user_requests as user_request_interfaces
from pytest_clerk_mock.services.organization_memberships import MockOrganizationMembershipsClient
from pytest_clerk_mock.services.organizations import MockOrganizationsClient
from pytest_clerk_mock.services.users import MockUsersClient

USERS_METHOD_NAMES: Final[tuple[str, ...]] = (
    "create",
    "create_async",
    "get",
    "get_async",
    "list",
    "list_async",
    "update",
    "update_async",
    "delete",
    "delete_async",
    "count",
    "count_async",
    "get_organization_memberships",
    "get_organization_memberships_async",
)
ORGANIZATIONS_METHOD_NAMES: Final[tuple[str, ...]] = (
    "create",
    "create_async",
    "get",
    "get_async",
    "list",
    "list_async",
    "update",
    "update_async",
    "delete",
    "delete_async",
)
ORGANIZATION_MEMBERSHIPS_METHOD_NAMES: Final[tuple[str, ...]] = (
    "create",
    "create_async",
    "list",
    "list_async",
    "update",
    "update_async",
    "delete",
    "delete_async",
)
SELF_PARAMETER_NAME: Final[str] = "self"
RETURN_KEY: Final[str] = "return"


def _callable_name(callable_obj: Any) -> str:
    """Return a stable label for a callable."""

    return f"{callable_obj.__module__}.{callable_obj.__qualname__}"


def _get_public_method(owner: type[object], method_name: str) -> Any:
    """Return a public method and fail clearly when it is missing."""

    method = getattr(owner, method_name, None)

    assert method is not None, f"{owner.__name__} is missing public method {method_name!r}"

    return method


def _get_public_attribute(owner: object, attribute_name: str) -> Any:
    """Return a module or class attribute and fail clearly when it is missing."""

    attribute = getattr(owner, attribute_name, None)
    owner_name = getattr(owner, "__name__", type(owner).__name__)

    assert attribute is not None, f"{owner_name} is missing public attribute {attribute_name!r}"

    return attribute


def _build_signature_spec(
    callable_obj: Any,
) -> tuple[list[tuple[str, inspect._ParameterKind, Any, Any]], Any]:
    """Return comparable parameter and return specs for a callable."""

    signature = inspect.signature(callable_obj)
    hints = get_type_hints(callable_obj, include_extras=True)
    parameters: list[tuple[str, inspect._ParameterKind, Any, Any]] = []

    for name, parameter in signature.parameters.items():
        if name == SELF_PARAMETER_NAME:
            continue

        parameters.append(
            (
                name,
                parameter.kind,
                hints.get(name, parameter.annotation),
                parameter.default,
            )
        )

    return parameters, hints.get(RETURN_KEY, signature.return_annotation)


def _build_pydantic_field_spec(model_cls: type[models.GetUserListRequest]) -> dict[str, tuple[Any, Any]]:
    """Return comparable field specs for a Clerk Pydantic request model."""

    return {
        field_name: (field_info.annotation, field_info.default)
        for field_name, field_info in model_cls.model_fields.items()
    }


def _build_protocol_field_spec(protocol_cls: type[Protocol]) -> dict[str, tuple[Any, Any]]:
    """Return comparable field specs for a protocol-backed request shape."""

    hints = get_type_hints(protocol_cls, include_extras=True)

    return {
        field_name: (annotation, getattr(protocol_cls, field_name, inspect._empty))
        for field_name, annotation in hints.items()
    }


def _build_typed_dict_field_spec(typed_dict_cls: type[object]) -> dict[str, Any]:
    """Return comparable field specs for a TypedDict request shape."""

    return get_type_hints(typed_dict_cls, include_extras=True)


def assert_signature_matches(real_callable: Any, mock_callable: Any) -> None:
    """Assert that two public callables have identical signatures."""

    real_parameters, real_return = _build_signature_spec(real_callable)
    mock_parameters, mock_return = _build_signature_spec(mock_callable)

    assert real_parameters == mock_parameters, (
        f"Signature mismatch for {_callable_name(mock_callable)} compared with "
        f"{_callable_name(real_callable)}\n"
        f"real={real_parameters!r}\n"
        f"mock={mock_parameters!r}"
    )
    assert real_return == mock_return, (
        f"Return annotation mismatch for {_callable_name(mock_callable)} compared with "
        f"{_callable_name(real_callable)}\n"
        f"real={real_return!r}\n"
        f"mock={mock_return!r}"
    )


def assert_pydantic_model_fields_match(
    real_model: type[object],
    mock_protocol_or_model: type[object],
) -> None:
    """Assert that request-model field names, types, and defaults match exactly."""

    real_fields = _build_pydantic_field_spec(real_model)
    mock_fields = _build_protocol_field_spec(mock_protocol_or_model)

    assert real_fields == mock_fields, (
        f"Field mismatch for {mock_protocol_or_model.__module__}.{mock_protocol_or_model.__qualname__} "
        f"compared with {real_model.__module__}.{real_model.__qualname__}\n"
        f"real={real_fields!r}\n"
        f"mock={mock_fields!r}"
    )


def assert_typed_dict_matches(real_typed_dict: type[object], mock_typed_dict: type[object]) -> None:
    """Assert that TypedDict field names and types match exactly."""

    real_fields = _build_typed_dict_field_spec(real_typed_dict)
    mock_fields = _build_typed_dict_field_spec(mock_typed_dict)

    assert real_fields == mock_fields, (
        f"TypedDict mismatch for {mock_typed_dict.__module__}.{mock_typed_dict.__qualname__} "
        f"compared with {real_typed_dict.__module__}.{real_typed_dict.__qualname__}\n"
        f"real={real_fields!r}\n"
        f"mock={mock_fields!r}"
    )


class TestUsersMethodContract:
    """Assert strict contract for the public Users SDK surface."""

    @pytest.mark.parametrize("method_name", USERS_METHOD_NAMES)
    def test_method_signature_matches_real_sdk(self, method_name: str) -> None:
        """Test that each compared users method matches the real Clerk SDK."""

        real_method = _get_public_method(Users, method_name)
        mock_method = _get_public_method(MockUsersClient, method_name)

        assert_signature_matches(real_method, mock_method)


class TestOrganizationsMethodContract:
    """Assert strict contract for the public Organizations SDK surface."""

    @pytest.mark.parametrize("method_name", ORGANIZATIONS_METHOD_NAMES)
    def test_method_signature_matches_real_sdk(self, method_name: str) -> None:
        """Test that each compared organizations method matches the real Clerk SDK."""

        real_method = _get_public_method(OrganizationsSDK, method_name)
        mock_method = _get_public_method(MockOrganizationsClient, method_name)

        assert_signature_matches(real_method, mock_method)


class TestOrganizationMembershipsMethodContract:
    """Assert strict contract for the public OrganizationMemberships SDK surface."""

    @pytest.mark.parametrize("method_name", ORGANIZATION_MEMBERSHIPS_METHOD_NAMES)
    def test_method_signature_matches_real_sdk(self, method_name: str) -> None:
        """Test that each compared membership method matches the real Clerk SDK."""

        real_method = _get_public_method(OrganizationMembershipsSDK, method_name)
        mock_method = _get_public_method(MockOrganizationMembershipsClient, method_name)

        assert_signature_matches(real_method, mock_method)


class TestRequestModelContract:
    """Assert strict contract for request model and request-shape types."""

    def test_get_user_list_request_matches_mock_protocol(self) -> None:
        """Test that the user list request fields match the mock protocol exactly."""

        assert_pydantic_model_fields_match(
            models.GetUserListRequest,
            _get_public_attribute(user_request_interfaces, "GetUserListRequestLike"),
        )

    def test_create_organization_request_matches_mock_protocol(self) -> None:
        """Test that the organization create request fields match the mock protocol exactly."""

        assert_pydantic_model_fields_match(
            models.CreateOrganizationRequestBody,
            _get_public_attribute(organization_request_interfaces, "CreateOrganizationRequestBody"),
        )
