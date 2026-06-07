from datetime import timezone as dt_timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    """
    Base schema for API request validation.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EmptySchema(ApiModel):
    """
    Empty request body schema.
    """


class IdBody(ApiModel):
    """
    Request body containing a user id.
    """

    user_id: Optional[int] = Field(default=None, ge=1)


JsonDict = Dict[str, Any]
JsonList = List[Any]


def as_utc_aware(value):
    """Treat naive datetimes as UTC and return aware UTC datetime."""

    if value.tzinfo is None:
        return value.replace(tzinfo=dt_timezone.utc)

    return value.astimezone(dt_timezone.utc)
