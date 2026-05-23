from datetime import datetime

from pydantic import Field, model_validator

from app.api.schemas.base import ApiModel
from app.api.schemas.limits import DESCRIPTION_MAX_LENGTH


INTERVAL_SECONDS = {
    "minutes": 60,
    "hours": 3600,
    "days": 86400,
    "weeks": 604800,
}


class RotationCreateSchema(ApiModel):
    """
    Validate rotation creation input.
    """

    team_id: int = Field(ge=1)
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    start_at: datetime
    rotation_type: str = Field(default="daily", pattern=r"^(daily|weekly|custom)$")
    interval_value: int = Field(default=1, ge=1, le=365)
    interval_unit: str = Field(default="days", pattern=r"^(minutes|hours|days|weeks)$")
    handoff_time: str = Field(default="09:00", pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    handoff_weekday: int | None = Field(default=None, ge=0, le=6)
    timezone: str = Field(default="UTC", min_length=1, max_length=64)
    duration_seconds: int | None = Field(default=None, ge=60)
    reminder_interval_seconds: int = Field(default=300, ge=0, le=2592000)
    add_team_members: bool = True
    enabled: bool = True

    @model_validator(mode="after")
    def set_duration(self):
        """
        Calculate duration from interval fields.
        """

        if self.reminder_interval_seconds != 0 and self.reminder_interval_seconds < 60:
            raise ValueError("reminder_interval_seconds must be 0 or at least 1 minute")

        if self.rotation_type == "daily":
            self.interval_value = 1
            self.interval_unit = "days"
            self.duration_seconds = 86400
        elif self.rotation_type == "weekly":
            self.interval_value = 1
            self.interval_unit = "weeks"
            self.duration_seconds = 604800
            if self.handoff_weekday is None:
                self.handoff_weekday = 0
        elif self.rotation_type == "custom":
            self.duration_seconds = self.interval_value * INTERVAL_SECONDS[self.interval_unit]

        return self


class RotationMemberAddSchema(ApiModel):
    """
    Validate rotation member input.
    """

    user_id: int = Field(ge=1)
    position: int = Field(ge=0, le=1000)


class RotationOverrideCreateSchema(ApiModel):
    """
    Validate rotation override input.
    """

    user_id: int = Field(ge=1)
    starts_at: datetime
    ends_at: datetime
    reason: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)

    @model_validator(mode="after")
    def validate_range(self):
        """
        Validate override time range.
        """

        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be greater than starts_at")
        return self


class RotationUpdateSchema(RotationCreateSchema):
    """
    Validate rotation update input.
    """


class RotationMemberUpdateSchema(ApiModel):
    """
    Validate rotation member update input.
    """

    position: int = Field(ge=0, le=1000)
    active: bool = True


class RotationLayerCreateSchema(ApiModel):
    """Validate rotation layer creation input."""

    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    priority: int = Field(default=0, ge=0, le=1000)

    start_at: datetime | None = None
    rotation_type: str | None = Field(default=None, pattern=r"^(daily|weekly|custom)$")
    interval_value: int | None = Field(default=None, ge=1, le=365)
    interval_unit: str | None = Field(default=None, pattern=r"^(minutes|hours|days|weeks)$")
    handoff_time: str | None = Field(
        default=None,
        pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$",
    )
    handoff_weekday: int | None = Field(default=None, ge=0, le=6)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    duration_seconds: int | None = Field(default=None, ge=60)
    enabled: bool = True

    @model_validator(mode="after")
    def set_duration(self):
        if self.rotation_type == "daily":
            self.interval_value = 1
            self.interval_unit = "days"
            self.duration_seconds = 86400
        elif self.rotation_type == "weekly":
            self.interval_value = 1
            self.interval_unit = "weeks"
            self.duration_seconds = 604800
            if self.handoff_weekday is None:
                self.handoff_weekday = 0
        elif self.rotation_type == "custom":
            if not self.interval_value:
                self.interval_value = 1
            if not self.interval_unit:
                self.interval_unit = "days"
            self.duration_seconds = self.interval_value * INTERVAL_SECONDS[self.interval_unit]

        return self


class RotationLayerUpdateSchema(RotationLayerCreateSchema):
    """Validate rotation layer update input."""


class RotationLayerMemberAddSchema(ApiModel):
    """Validate layer member input."""

    user_id: int = Field(ge=1)
    position: int = Field(ge=0, le=1000)


class RotationLayerMemberUpdateSchema(ApiModel):
    """Validate layer member update input."""

    position: int = Field(ge=0, le=1000)
    active: bool = True


class RotationLayerRestrictionSchema(ApiModel):
    """Validate one layer restriction."""

    weekday: int | None = Field(default=None, ge=0, le=6)
    start_time: str = Field(pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    end_time: str = Field(pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$")


class RotationLayerRestrictionsReplaceSchema(ApiModel):
    """Validate replacing layer restrictions."""

    restrictions: list[RotationLayerRestrictionSchema] = Field(default_factory=list)
