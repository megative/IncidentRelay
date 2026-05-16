from typing import List, Optional

from pydantic import EmailStr, Field, field_validator

from app.api.schemas.base import ApiModel
from app.api.schemas.limits import (
    CONTACT_ID_MAX_LENGTH,
    DISPLAY_NAME_MAX_LENGTH,
    PHONE_MAX_LENGTH,
    TOKEN_NAME_MAX_LENGTH,
    TOKEN_NAME_MIN_LENGTH,
    validate_phone,
)


class ProfileUpdateSchema(ApiModel):
    """Current user profile update request."""

    display_name: Optional[str] = Field(
        default=None,
        max_length=DISPLAY_NAME_MAX_LENGTH,
    )
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(
        default=None,
        max_length=PHONE_MAX_LENGTH,
    )
    telegram_user_id: Optional[str] = Field(
        default=None,
        max_length=CONTACT_ID_MAX_LENGTH,
    )
    slack_user_id: Optional[str] = Field(
        default=None,
        max_length=CONTACT_ID_MAX_LENGTH,
    )
    mattermost_user_id: Optional[str] = Field(
        default=None,
        max_length=CONTACT_ID_MAX_LENGTH,
    )

    @field_validator("phone")
    @classmethod
    def validate_phone_field(cls, value):
        """Validate profile phone number."""
        return validate_phone(value)


class ProfileTokenCreateSchema(ApiModel):
    """Personal API token creation request."""

    name: str = Field(
        default="personal-api-token",
        min_length=TOKEN_NAME_MIN_LENGTH,
        max_length=TOKEN_NAME_MAX_LENGTH,
    )
    group_id: Optional[int] = Field(default=None, ge=1)
    scopes: List[str] = Field(default_factory=lambda: ["alerts:read"])
    days: int = Field(default=0, ge=0)


class ActiveGroupSchema(ApiModel):
    """Active group selection request."""

    group_id: Optional[int] = Field(default=None, ge=1)
