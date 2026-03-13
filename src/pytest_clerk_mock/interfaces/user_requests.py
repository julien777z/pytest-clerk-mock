from typing import List, Protocol


class GetUserListRequestLike(Protocol):
    """Describe the supported user list request shape."""

    email_address: List[str] | None = None
    phone_number: List[str] | None = None
    external_id: List[str] | None = None
    username: List[str] | None = None
    web3_wallet: List[str] | None = None
    user_id: List[str] | None = None
    organization_id: List[str] | None = None
    query: str | None = None
    email_address_query: str | None = None
    phone_number_query: str | None = None
    username_query: str | None = None
    name_query: str | None = None
    banned: bool | None = None
    last_active_at_before: int | None = None
    last_active_at_after: int | None = None
    last_active_at_since: int | None = None
    created_at_before: int | None = None
    created_at_after: int | None = None
    limit: int | None = 10
    offset: int | None = 0
    order_by: str | None = "-created_at"
