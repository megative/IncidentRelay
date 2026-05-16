from typing import Optional

from pydantic import Field

from app.api.schemas.base import ApiModel
from app.api.schemas.limits import (
    DESCRIPTION_MAX_LENGTH,
    NAME_MAX_LENGTH,
    SLUG_MAX_LENGTH,
    SLUG_MIN_LENGTH,
)


class GroupCreateSchema(ApiModel):
    """Group creation request."""

    slug: str = Field(
        min_length=SLUG_MIN_LENGTH,
        max_length=SLUG_MAX_LENGTH,
        pattern=r"^[a-z0-9][a-z0-9_-]*$",
    )
    name: str = Field(min_length=2, max_length=NAME_MAX_LENGTH)
    description: Optional[str] = Field(
        default=None,
        max_length=DESCRIPTION_MAX_LENGTH,
    )


class GroupUpdateSchema(ApiModel):
    """Group update request."""

    slug: str = Field(
        min_length=SLUG_MIN_LENGTH,
        max_length=SLUG_MAX_LENGTH,
        pattern=r"^[a-z0-9][a-z0-9_-]*$",
    )
    name: str = Field(min_length=2, max_length=NAME_MAX_LENGTH)
    description: Optional[str] = Field(
        default=None,
        max_length=DESCRIPTION_MAX_LENGTH,
    )
    active: bool = True


class UserGroupAddSchema(ApiModel):
    """Group membership request."""

    user_id: int = Field(ge=1)
    role: str = Field(default="read_only", pattern="^(read_only|rw)$")


class UserGroupUpdateSchema(ApiModel):
    """Group membership update request."""

    role: str = Field(default="read_only", pattern="^(read_only|rw)$")
    active: bool = True
