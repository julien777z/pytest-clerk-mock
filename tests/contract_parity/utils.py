import inspect
from typing import Any, Final, get_args, get_origin, get_type_hints

from clerk_backend_api import models
from clerk_backend_api.organizationmemberships_sdk import OrganizationMembershipsSDK
from clerk_backend_api.organizations_sdk import OrganizationsSDK
from clerk_backend_api.users import Users

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


def callable_name(callable_obj: Any) -> str:
    """Return a stable label for a callable."""

    return f"{callable_obj.__module__}.{callable_obj.__qualname__}"


def discover_public_methods(owner: type[object]) -> dict[str, Any]:
    """Return all public callable attributes for a class."""

    return {
        name: member
        for name, member in inspect.getmembers(owner, predicate=callable)
        if not name.startswith("_")
    }


def build_signature_spec(
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


def iter_annotation_types(annotation: Any) -> set[type[object]]:
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
        referenced_types.update(iter_annotation_types(arg))

    return referenced_types


def iter_referenced_model_types(callable_obj: Any) -> set[type[object]]:
    """Return Clerk model/request types referenced by a callable annotation set."""

    _, return_annotation = build_signature_spec(callable_obj)
    hints = get_type_hints(callable_obj, include_extras=True)
    referenced_types = iter_annotation_types(return_annotation)

    for annotation in hints.values():
        referenced_types.update(iter_annotation_types(annotation))

    return {
        referenced_type
        for referenced_type in referenced_types
        if referenced_type.__module__.startswith("clerk_backend_api.models")
    }


def build_model_field_report(
    real_model: type[object],
    mock_model: type[object],
) -> dict[str, set[str]]:
    """Return a field coverage report for a real Clerk model and mock model."""

    real_fields = set(real_model.model_fields)
    mock_fields = set(mock_model.model_fields)

    return {
        "missing_fields": real_fields - mock_fields,
        "extra_fields": mock_fields - real_fields,
    }


def assert_model_fields_cover_real_model(
    real_model: type[object],
    mock_model: type[object],
    *,
    allowed_extra_fields: frozenset[str],
) -> None:
    """Assert that a mock model covers the real Clerk model fields."""

    field_report = build_model_field_report(real_model, mock_model)

    assert field_report["missing_fields"] == set(), (
        f"{mock_model.__name__} is missing Clerk fields from {real_model.__name__}: "
        f"{sorted(field_report['missing_fields'])!r}"
    )
    assert field_report["extra_fields"] <= set(allowed_extra_fields), (
        f"{mock_model.__name__} has unexpected extra fields compared with {real_model.__name__}: "
        f"{sorted(field_report['extra_fields'])!r}"
    )


def assert_signature_matches(real_callable: Any, mock_callable: Any) -> None:
    """Assert that two public callables have identical signatures."""

    real_parameters, real_return = build_signature_spec(real_callable)
    mock_parameters, mock_return = build_signature_spec(mock_callable)

    assert real_parameters == mock_parameters, (
        f"Signature mismatch for {callable_name(mock_callable)} compared with "
        f"{callable_name(real_callable)}\n"
        f"real={real_parameters!r}\n"
        f"mock={mock_parameters!r}"
    )
    assert real_return == mock_return, (
        f"Return annotation mismatch for {callable_name(mock_callable)} compared with "
        f"{callable_name(real_callable)}\n"
        f"real={real_return!r}\n"
        f"mock={mock_return!r}"
    )
