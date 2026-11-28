from enum import StrEnum


class ClerkErrorCode(StrEnum):
    """Error codes the mock returns in ClerkErrors payloads."""

    EMAIL_EXISTS = "form_identifier_exists"
    INVALID_FORMAT = "form_param_format_invalid"
    MOCK_ERROR = "mock_error"
    RESOURCE_NOT_FOUND = "resource_not_found"
