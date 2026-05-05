from pydantic import EmailStr, Field

from app.api.schemas.base import ApiModel


class UserBaseSchema(ApiModel):
    """Base schema for user input."""

    username: str = Field(min_length=2, max_length=80, pattern=r"^[a-zA-Z0-9._-]+$")
    display_name: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=64)
    telegram_chat_id: str | None = Field(default=None, max_length=128)
    slack_user_id: str | None = Field(default=None, max_length=128)
    mattermost_user_id: str | None = Field(default=None, max_length=128)
    active: bool = True
    is_admin: bool = False
    password: str | None = Field(default=None, min_length=8, max_length=256)


class UserCreateSchema(UserBaseSchema):
    """Validate user creation input."""

    group_id: int | None = Field(default=None, ge=1)
    group_role: str = Field(default="read_only", pattern="^(read_only|rw)$")


class UserUpdateSchema(UserBaseSchema):
    """Validate user update input."""
