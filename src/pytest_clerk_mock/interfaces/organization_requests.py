from typing import Any, Dict, TypeAlias

from clerk_backend_api import models
from clerk_backend_api.types import UNSET, OptionalNullable
from pydantic.fields import PydanticUndefined

MetadataDict: TypeAlias = Dict[str, Any]
CreateOrganizationRequestBodyTypedDict = models.CreateOrganizationRequestBodyTypedDict
CreateOrganizationRequest: TypeAlias = (
    models.CreateOrganizationRequestBody | models.CreateOrganizationRequestBodyTypedDict
)


class CreateOrganizationRequestBody:
    """Describe the Clerk organization create request model shape."""

    name: str = PydanticUndefined
    created_by: OptionalNullable[str] = UNSET
    private_metadata: OptionalNullable[Dict[str, Any]] = UNSET
    public_metadata: OptionalNullable[Dict[str, Any]] = UNSET
    slug: OptionalNullable[str] = UNSET
    max_allowed_memberships: OptionalNullable[int] = UNSET
    created_at: OptionalNullable[str] = UNSET
