from pydantic import Field

from app.api.schemas.base import ApiModel
from app.api.schemas.limits import (
    DESCRIPTION_MAX_LENGTH,
    NAME_MAX_LENGTH,
    NAME_MIN_LENGTH,
    ROLE_MAX_LENGTH,
    SLUG_MAX_LENGTH,
    SLUG_MIN_LENGTH,
)
from app.api.schemas.roles import TEAM_ROLE_PATTERN, TEAM_VIEWER_ROLE


class TeamBaseSchema(ApiModel):
    """Base schema for team input."""

    group_id: int = Field(ge=1)
    slug: str = Field(
        min_length=SLUG_MIN_LENGTH,
        max_length=SLUG_MAX_LENGTH,
        pattern=r"^[a-z0-9][a-z0-9_-]*$",
    )
    name: str = Field(min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    escalation_enabled: bool = True
    escalation_after_reminders: int = Field(default=2, ge=0, le=100)
    active: bool = True


class TeamCreateSchema(TeamBaseSchema):
    """Validate team creation input."""


class TeamUpdateSchema(TeamBaseSchema):
    """Validate team update input."""


class TeamUserAddSchema(ApiModel):
    """Validate team membership input."""

    user_id: int = Field(ge=1)
    role: str = Field(
        default=TEAM_VIEWER_ROLE,
        max_length=ROLE_MAX_LENGTH,
        pattern=TEAM_ROLE_PATTERN,
    )


class TeamUserUpdateSchema(ApiModel):
    """Validate team membership update input."""

    role: str = Field(
        default=TEAM_VIEWER_ROLE,
        max_length=ROLE_MAX_LENGTH,
        pattern=TEAM_ROLE_PATTERN,
    )
    active: bool = True
