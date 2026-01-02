from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field


class MockEmailAddress(BaseModel):
    """Represents a Clerk email address object."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    email_address: str
    verification: dict | None = None
    linked_to: list[dict] = Field(default_factory=list)

    @classmethod
    def create(cls, email: str, email_id: str) -> Self:
        """Create a verified email address."""

        return cls(
            id=email_id,
            email_address=email,
            verification={"status": "verified", "strategy": "email_code"},
            linked_to=[],
        )


class MockPhoneNumber(BaseModel):
    """Represents a Clerk phone number object."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    phone_number: str
    verification: dict | None = None
    linked_to: list[dict] = Field(default_factory=list)

    @classmethod
    def create(cls, phone: str, phone_id: str) -> Self:
        """Create a verified phone number."""

        return cls(
            id=phone_id,
            phone_number=phone,
            verification={"status": "verified", "strategy": "phone_code"},
            linked_to=[],
        )


class MockUser(BaseModel):
    """Represents a Clerk User object."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    external_id: str | None = None
    primary_email_address_id: str | None = None
    primary_phone_number_id: str | None = None
    primary_web3_wallet_id: str | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    profile_image_url: str = ""
    image_url: str = ""
    has_image: bool = False
    public_metadata: dict = Field(default_factory=dict)
    private_metadata: dict = Field(default_factory=dict)
    unsafe_metadata: dict = Field(default_factory=dict)
    email_addresses: list[MockEmailAddress] = Field(default_factory=list)
    phone_numbers: list[MockPhoneNumber] = Field(default_factory=list)
    web3_wallets: list[dict] = Field(default_factory=list)
    passkeys: list[dict] = Field(default_factory=list)
    password_enabled: bool = False
    two_factor_enabled: bool = False
    totp_enabled: bool = False
    backup_code_enabled: bool = False
    external_accounts: list[dict] = Field(default_factory=list)
    saml_accounts: list[dict] = Field(default_factory=list)
    last_sign_in_at: int | None = None
    banned: bool = False
    locked: bool = False
    lockout_expires_in_seconds: int | None = None
    verification_attempts_remaining: int | None = None
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    updated_at: int = Field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    delete_self_enabled: bool = True
    create_organization_enabled: bool = True
    last_active_at: int | None = None
    create_organizations_limit: int | None = None
    legal_accepted_at: int | None = None

