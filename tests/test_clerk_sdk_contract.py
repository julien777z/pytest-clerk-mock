import inspect
from typing import Any, Final, get_args, get_origin, get_type_hints

import pytest
from clerk_backend_api import models
from clerk_backend_api.organizationmemberships_sdk import OrganizationMembershipsSDK
from clerk_backend_api.organizations_sdk import OrganizationsSDK
from clerk_backend_api.users import Users

from pytest_clerk_mock.client import MockClerkClient
from pytest_clerk_mock.models.organization import MockOrganization, MockOrganizationMembership
from pytest_clerk_mock.models.user import MockUser
from pytest_clerk_mock.services.organization_memberships import MockOrganizationMembershipsClient
from pytest_clerk_mock.services.organizations import MockOrganizationsClient
from pytest_clerk_mock.services.users import MockUsersClient

SELF_PARAMETER_NAME: Final[str] = "self"
RETURN_KEY: Final[str] = "return"
SERVICE_CONTRACTS: Final[
    tuple[tuple[type[object], type[object], frozenset[str]], ...]
] = (
    (Users, MockUsersClient, frozenset({"reset", "set_organization_memberships"})),
    (OrganizationsSDK, MockOrganizationsClient, frozenset({"add", "reset"})),
    (OrganizationMembershipsSDK, MockOrganizationMembershipsClient, frozenset({"get", "reset"})),
)
EXPECTED_CLIENT_PROPERTIES: Final[dict[str, type[object]]] = {
    "users": MockUsersClient,
    "organizations": MockOrganizationsClient,
    "organization_memberships": MockOrganizationMembershipsClient,
}
EXPECTED_CLIENT_METHODS: Final[frozenset[str]] = frozenset(
    {
        "add_organization_membership",
        "as_clerk_user",
        "as_user",
        "authenticate_request",
        "configure_auth",
        "configure_auth_from_user",
        "reset",
    }
)
EXPORTED_MODEL_CONTRACTS: Final[
    tuple[tuple[type[object], type[object], frozenset[str]], ...]
] = (
    (models.User, MockUser, frozenset()),
    (models.Organization, MockOrganization, frozenset()),
    (models.OrganizationMembership, MockOrganizationMembership, frozenset({"organization_id", "user_id"})),
)


def _callable_name(callable_obj: Any) -> str:
    """Return a stable label for a callable."""

    return f"{callable_obj.__module__}.{callable_obj.__qualname__}"


def _discover_public_methods(owner: type[object]) -> dict[str, Any]:
    """Return all public callable attributes for a class."""

    return {
        name: member
        for name, member in inspect.getmembers(owner, predicate=callable)
        if not name.startswith("_")
    }


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


def _iter_annotation_types(annotation: Any) -> set[type[object]]:
    """Flatten nested annotations into the concrete types they reference."""

    if annotation is inspect._empty:
        return set()

    origin = get_origin(annotation)
    if origin is None:
        if isinstance(annotation, type):
            return {annotation}

        return set()

    referenced_types: set[type[object]] = set()

    for arg in get_args(annotation):
        referenced_types.update(_iter_annotation_types(arg))

    return referenced_types


def _iter_referenced_model_types(callable_obj: Any) -> set[type[object]]:
    """Return Clerk model/request types referenced by a callable annotation set."""

    _, return_annotation = _build_signature_spec(callable_obj)
    hints = get_type_hints(callable_obj, include_extras=True)
    referenced_types = _iter_annotation_types(return_annotation)

    for annotation in hints.values():
        referenced_types.update(_iter_annotation_types(annotation))

    return {
        referenced_type
        for referenced_type in referenced_types
        if referenced_type.__module__.startswith("clerk_backend_api.models")
    }


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


class TestSdkServiceContracts:
    """Assert strict contract coverage for public Clerk SDK services."""

    @pytest.mark.parametrize(
        ("real_owner", "mock_owner", "helper_only_methods"),
        SERVICE_CONTRACTS,
    )
    def test_mock_supports_every_public_sdk_method(
        self,
        real_owner: type[object],
        mock_owner: type[object],
        helper_only_methods: frozenset[str],
    ) -> None:
        """Test that each mock service implements every public Clerk SDK method."""

        real_method_names = set(_discover_public_methods(real_owner))
        mock_method_names = set(_discover_public_methods(mock_owner))

        assert real_method_names - mock_method_names == set(), (
            f"{mock_owner.__name__} is missing SDK methods from {real_owner.__name__}: "
            f"{sorted(real_method_names - mock_method_names)!r}"
        )
        assert mock_method_names - real_method_names == set(helper_only_methods), (
            f"{mock_owner.__name__} has undocumented helper methods beyond the Clerk SDK: "
            f"{sorted(mock_method_names - real_method_names)!r}"
        )

    @pytest.mark.parametrize(
        ("real_owner", "mock_owner", "_helper_only_methods"),
        SERVICE_CONTRACTS,
    )
    def test_all_public_sdk_signatures_match(
        self,
        real_owner: type[object],
        mock_owner: type[object],
        _helper_only_methods: frozenset[str],
    ) -> None:
        """Test that every public Clerk SDK method matches the mock signature exactly."""

        real_methods = _discover_public_methods(real_owner)
        mock_methods = _discover_public_methods(mock_owner)

        for method_name in sorted(real_methods):
            assert_signature_matches(real_methods[method_name], mock_methods[method_name])


class TestTypeContracts:
    """Assert that mock signatures use real Clerk request and object types."""

    @pytest.mark.parametrize(
        ("real_owner", "mock_owner", "_helper_only_methods"),
        SERVICE_CONTRACTS,
    )
    def test_method_annotations_only_reference_real_clerk_types(
        self,
        real_owner: type[object],
        mock_owner: type[object],
        _helper_only_methods: frozenset[str],
    ) -> None:
        """Test that method annotations reuse real Clerk request/model types directly."""

        real_methods = _discover_public_methods(real_owner)
        mock_methods = _discover_public_methods(mock_owner)

        for method_name in sorted(real_methods):
            real_types = _iter_referenced_model_types(real_methods[method_name])
            mock_types = _iter_referenced_model_types(mock_methods[method_name])

            assert real_types == mock_types, (
                f"Referenced Clerk types mismatch for {mock_owner.__name__}.{method_name}\n"
                f"real={sorted(type_.__name__ for type_ in real_types)!r}\n"
                f"mock={sorted(type_.__name__ for type_ in mock_types)!r}"
            )

    @pytest.mark.parametrize(
        ("real_model", "mock_model", "allowed_extra_fields"),
        EXPORTED_MODEL_CONTRACTS,
    )
    def test_exported_mock_models_cover_real_model_fields(
        self,
        real_model: type[object],
        mock_model: type[object],
        allowed_extra_fields: frozenset[str],
    ) -> None:
        """Test that exported mock models include the real Clerk model fields."""

        real_fields = set(real_model.model_fields)
        mock_fields = set(mock_model.model_fields)

        assert real_fields - mock_fields == set(), (
            f"{mock_model.__name__} is missing Clerk fields from {real_model.__name__}: "
            f"{sorted(real_fields - mock_fields)!r}"
        )
        assert mock_fields - real_fields <= set(allowed_extra_fields), (
            f"{mock_model.__name__} has unexpected extra fields compared with {real_model.__name__}: "
            f"{sorted(mock_fields - real_fields)!r}"
        )


class TestMockClerkClientContract:
    """Assert the public top-level MockClerkClient surface."""

    def test_service_properties_match_expected_types(self) -> None:
        """Test that the top-level service properties are attached with stable types."""

        client = MockClerkClient()

        for property_name, expected_type in EXPECTED_CLIENT_PROPERTIES.items():
            assert isinstance(getattr(client, property_name), expected_type)

    def test_public_client_methods_match_expected_surface(self) -> None:
        """Test that top-level mock client helpers stay stable and explicit."""

        client_method_names = set(_discover_public_methods(MockClerkClient))

        assert client_method_names == set(EXPECTED_CLIENT_METHODS)
