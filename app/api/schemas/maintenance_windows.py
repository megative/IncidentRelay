from __future__ import annotations

from datetime import datetime, timezone

from pydantic import Field, field_validator, model_validator

from app.api.schemas.base import ApiModel, as_utc_aware


MAINTENANCE_WINDOW_TITLE_MAX_LENGTH = 255
MAINTENANCE_WINDOW_DESCRIPTION_MAX_LENGTH = 2000


class MaintenanceWindowBaseSchema(ApiModel):
    """Base schema for maintenance window payloads."""

    service_id: int = Field(ge=1)

    title: str | None = Field(
        default=None,
        max_length=MAINTENANCE_WINDOW_TITLE_MAX_LENGTH,
    )

    description: str | None = Field(
        default=None,
        max_length=MAINTENANCE_WINDOW_DESCRIPTION_MAX_LENGTH,
    )

    start_at: datetime
    end_at: datetime

    enabled: bool = True

    @field_validator("start_at", "end_at")
    @classmethod
    def normalize_datetimes(cls, value: datetime) -> datetime:
        """Normalize API datetime values to UTC-aware datetime."""
        return as_utc_aware(value)

    @model_validator(mode="after")
    def validate_time_range(self):
        """Validate maintenance window time range."""
        now = datetime.now(timezone.utc)

        if self.end_at <= self.start_at:
            raise ValueError("end_at must be greater than start_at")

        if self.end_at <= now:
            raise ValueError("end_at must be in the future")

        return self


class MaintenanceWindowCreateSchema(MaintenanceWindowBaseSchema):
    """Validate maintenance window creation."""


class MaintenanceWindowUpdateSchema(MaintenanceWindowBaseSchema):
    """Validate maintenance window update."""


class MaintenanceWindowExtendSchema(ApiModel):
    """Validate maintenance window extension."""

    end_at: datetime

    @field_validator("end_at")
    @classmethod
    def normalize_end_at(cls, value: datetime) -> datetime:
        """Normalize API datetime value to UTC-aware datetime."""
        return as_utc_aware(value)

    @model_validator(mode="after")
    def validate_end_at(self):
        """Validate maintenance window extension end time."""
        now = datetime.now(timezone.utc)

        if self.end_at <= now:
            raise ValueError("end_at must be in the future")

        return self
