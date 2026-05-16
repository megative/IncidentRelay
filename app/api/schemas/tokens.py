from pydantic import Field

from app.api.schemas.base import ApiModel
from app.api.schemas.limits import TOKEN_NAME_MAX_LENGTH, TOKEN_NAME_MIN_LENGTH


class TokenCreateSchema(ApiModel):
    """Validate API token creation input."""

    team_id: int | None = Field(default=None, ge=1)
    name: str = Field(
        min_length=TOKEN_NAME_MIN_LENGTH,
        max_length=TOKEN_NAME_MAX_LENGTH,
    )
    scopes: list[str] = Field(default_factory=lambda: ["alerts:write"])
    days: int | None = Field(default=None, ge=1, le=3650)
