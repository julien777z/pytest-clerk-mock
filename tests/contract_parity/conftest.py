import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark every collected test in this folder as a contract test."""

    for item in items:
        item.add_marker(pytest.mark.contract)
