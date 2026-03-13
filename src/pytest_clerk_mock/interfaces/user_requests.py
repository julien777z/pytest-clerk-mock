from typing import Protocol


class GetUserListRequestLike(Protocol):
    """Describe the supported user list request shape."""

    email_address: list[str] | None
    phone_number: list[str] | None
    external_id: list[str] | None
    username: list[str] | None
    user_id: list[str] | None
    query: str | None
    last_active_at_since: int | None
    limit: int
    offset: int
    order_by: str
