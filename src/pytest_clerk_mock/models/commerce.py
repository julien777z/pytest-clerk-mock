from pydantic import BaseModel, Field


class MockCommerceSubscriptionItem(BaseModel):
    """Minimal commerce subscription line item for mock billing responses."""

    object: str = "commerce_subscription_item"
    id: str
    instance_id: str
    status: str
    plan_id: str | None
    plan_period: str
    payer_id: str
    is_free_trial: bool
    period_start: int
    period_end: int | None
    canceled_at: int | None
    past_due_at: int | None
    ended_at: int | None


class MockCommerceSubscription(BaseModel):
    """Minimal commerce subscription for mock billing responses (SDK-agnostic)."""

    object: str = "commerce_subscription"
    id: str
    instance_id: str
    status: str
    payer_id: str
    created_at: int
    updated_at: int
    active_at: int
    past_due_at: int | None
    subscription_items: list[MockCommerceSubscriptionItem] = Field(default_factory=list)
