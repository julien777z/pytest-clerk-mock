import pytest

from tests.contract_parity.utils import (
    assert_model_fields_cover_real_model,
    build_model_field_report,
)


class TestModelFieldCoverageUtils:
    """Assert that model field coverage helpers report missing fields clearly."""

    def test_model_field_report_lists_missing_fields(self) -> None:
        """Test that the field report includes omitted Clerk-style fields."""

        class _RealModel:
            model_fields = {
                "id": object(),
                "bypass_client_trust": object(),
            }

        class _MockModel:
            model_fields = {
                "id": object(),
            }

        field_report = build_model_field_report(_RealModel, _MockModel)

        assert field_report["missing_fields"] == {"bypass_client_trust"}
        assert field_report["extra_fields"] == set()

    def test_model_field_assertion_mentions_missing_field_name(self) -> None:
        """Test that the field assertion message names a missing field clearly."""

        class _RealModel:
            __name__ = "RealUser"
            model_fields = {
                "id": object(),
                "bypass_client_trust": object(),
            }

        class _MockModel:
            __name__ = "MockUser"
            model_fields = {
                "id": object(),
            }

        with pytest.raises(AssertionError, match="bypass_client_trust"):
            assert_model_fields_cover_real_model(
                _RealModel,
                _MockModel,
                allowed_extra_fields=frozenset(),
            )
