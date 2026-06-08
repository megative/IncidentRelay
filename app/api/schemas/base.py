from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.modules.common import as_naive_datetime


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
    return as_naive_datetime(value)
