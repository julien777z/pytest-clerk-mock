import pytest

from pytest_clerk_mock.client import MockClerkClient

from tests.contract_parity.utils import (
    EXPECTED_CLIENT_METHODS,
    EXPECTED_CLIENT_PROPERTIES,
    EXPORTED_MODEL_CONTRACTS,
    SERVICE_CONTRACTS,
    assert_model_fields_cover_real_model,
    assert_signature_matches,
    discover_public_methods,
    iter_referenced_model_types,
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

        real_method_names = set(discover_public_methods(real_owner))
        mock_method_names = set(discover_public_methods(mock_owner))

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

        real_methods = discover_public_methods(real_owner)
        mock_methods = discover_public_methods(mock_owner)

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

        real_methods = discover_public_methods(real_owner)
        mock_methods = discover_public_methods(mock_owner)

        for method_name in sorted(real_methods):
            real_types = iter_referenced_model_types(real_methods[method_name])
            mock_types = iter_referenced_model_types(mock_methods[method_name])

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

        assert_model_fields_cover_real_model(
            real_model,
            mock_model,
            allowed_extra_fields=allowed_extra_fields,
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

        client_method_names = set(discover_public_methods(MockClerkClient))

        assert client_method_names == set(EXPECTED_CLIENT_METHODS)
