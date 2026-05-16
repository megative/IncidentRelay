from pydantic import EmailStr, Field, field_validator

from app.api.schemas.base import ApiModel
from app.api.schemas.limits import (
    CONTACT_ID_MAX_LENGTH,
    DISPLAY_NAME_MAX_LENGTH,
    PHONE_MAX_LENGTH,
    USERNAME_MAX_LENGTH,
    USERNAME_MIN_LENGTH,
    validate_phone,
)


class UserBaseSchema(ApiModel):
    """Base schema for user input."""

    username: str = Field(
        min_length=USERNAME_MIN_LENGTH,
        max_length=USERNAME_MAX_LENGTH,
        pattern=r"^[a-zA-Z0-9._-]+$",
    )
    display_name: str | None = Field(
        default=None,
        max_length=DISPLAY_NAME_MAX_LENGTH,
    )
    email: EmailStr | None = None
    phone: str | None = Field(
        default=None,
        max_length=PHONE_MAX_LENGTH,
    )
    telegram_chat_id: str | None = Field(
        default=None,
        max_length=CONTACT_ID_MAX_LENGTH,
    )
    slack_user_id: str | None = Field(
        default=None,
        max_length=CONTACT_ID_MAX_LENGTH,
    )
    mattermost_user_id: str | None = Field(
        default=None,
        max_length=CONTACT_ID_MAX_LENGTH,
    )
    active: bool = True
    is_admin: bool = False
    password: str | None = Field(default=None, min_length=8, max_length=256)

    @field_validator("phone")
    @classmethod
    def validate_phone_field(cls, value):
        """Validate user phone number."""
        return validate_phone(value)


class UserCreateSchema(UserBaseSchema):
    """Validate user creation input."""

    group_id: int | None = Field(default=None, ge=1)
    group_role: str = Field(default="read_only", pattern="^(read_only|rw)$")


class UserUpdateSchema(UserBaseSchema):
    """Validate user update input."""
