from typing import TypeAlias

from clerk_backend_api.types import OptionalNullable
from typing_extensions import NotRequired, TypedDict

MetadataScalar: TypeAlias = str | int | float | bool | None
MetadataValue: TypeAlias = MetadataScalar | list["MetadataValue"] | dict[str, "MetadataValue"]
MetadataDict: TypeAlias = dict[str, MetadataValue]


class CreateOrganizationRequestBody(TypedDict):
    """Describe the supported organization create request shape."""

    name: str
    created_by: NotRequired[OptionalNullable[str]]
    private_metadata: NotRequired[OptionalNullable[MetadataDict]]
    public_metadata: NotRequired[OptionalNullable[MetadataDict]]
    slug: NotRequired[OptionalNullable[str]]
    max_allowed_memberships: NotRequired[OptionalNullable[int]]
    created_at: NotRequired[OptionalNullable[str]]
