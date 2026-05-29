from typing import Any, Dict, List

from pydantic import Field, model_validator

from app.api.schemas.base import ApiModel
from app.api.schemas.limits import (
    DESCRIPTION_MAX_LENGTH,
    NAME_MAX_LENGTH,
    NAME_MIN_LENGTH,
    SLUG_MAX_LENGTH,
    SLUG_MIN_LENGTH,
)


SERVICE_TYPE_PATTERN = (
    r"^(api|web|database|queue|cache|worker|cron|network|storage|"
    r"infrastructure|external|other)$"
)

SERVICE_ENVIRONMENT_PATTERN = r"^(production|staging|development|testing|shared)$"

SERVICE_CRITICALITY_PATTERN = r"^(low|medium|high|critical)$"

SERVICE_TIER_PATTERN = r"^(tier_1|tier_2|tier_3|tier_4)$"

SERVICE_STATUS_PATTERN = (
    r"^(operational|degraded|partial_outage|major_outage|"
    r"maintenance|disabled|unknown)$"
)

SERVICE_STATUS_SOURCE_PATTERN = r"^(manual|alerts|maintenance|system)$"

SERVICE_LINK_TYPE_PATTERN = (
    r"^(dashboard|metrics|logs|traces|repository|documentation|"
    r"status_page|wiki|other)$"
)

SERVICE_DEPENDENCY_TYPE_PATTERN = r"^(hard|soft|external|informational)$"

SERVICE_DEPENDENCY_CRITICALITY_PATTERN = r"^(required|important|optional)$"


class ServiceBaseSchema(ApiModel):
    """Validate service input."""

    team_id: int = Field(ge=1)

    slug: str = Field(
        min_length=SLUG_MIN_LENGTH,
        max_length=SLUG_MAX_LENGTH,
        pattern=r"^[a-z0-9][a-z0-9-]*$",
    )
    name: str = Field(
        min_length=NAME_MIN_LENGTH,
        max_length=NAME_MAX_LENGTH,
    )
    description: str | None = Field(
        default=None,
        max_length=DESCRIPTION_MAX_LENGTH,
    )

    service_type: str = Field(default="other", pattern=SERVICE_TYPE_PATTERN)
    environment: str = Field(default="production", pattern=SERVICE_ENVIRONMENT_PATTERN)
    criticality: str = Field(default="medium", pattern=SERVICE_CRITICALITY_PATTERN)
    tier: str = Field(default="tier_3", pattern=SERVICE_TIER_PATTERN)

    status: str = Field(default="operational", pattern=SERVICE_STATUS_PATTERN)
    status_source: str = Field(default="manual", pattern=SERVICE_STATUS_SOURCE_PATTERN)
    status_message: str | None = Field(
        default=None,
        max_length=DESCRIPTION_MAX_LENGTH,
    )

    default_rotation_id: int | None = Field(default=None, ge=1)
    default_escalation_policy_id: int | None = Field(default=None, ge=1)

    labels: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    enabled: bool = True
    public: bool = False
    public_name: str | None = Field(
        default=None,
        min_length=NAME_MIN_LENGTH,
        max_length=NAME_MAX_LENGTH,
    )
    public_description: str | None = Field(
        default=None,
        max_length=DESCRIPTION_MAX_LENGTH,
    )
    public_order: int = Field(default=100, ge=0)


class ServiceCreateSchema(ServiceBaseSchema):
    """Validate service creation."""


class ServiceUpdateSchema(ServiceBaseSchema):
    """Validate service update."""


class ServiceMatchRuleBaseSchema(ApiModel):
    """Validate service match rule input."""

    team_id: int = Field(ge=1)
    route_id: int | None = Field(default=None, ge=1)
    service_id: int = Field(ge=1)

    position: int = Field(default=0, ge=0)
    name: str = Field(
        min_length=NAME_MIN_LENGTH,
        max_length=NAME_MAX_LENGTH,
    )
    description: str | None = Field(
        default=None,
        max_length=DESCRIPTION_MAX_LENGTH,
    )
    matchers: Dict[str, Any] = Field(default_factory=dict)

    enabled: bool = True

    @model_validator(mode="after")
    def validate_matchers(self):
        """Require at least one matcher."""
        if not self.matchers:
            raise ValueError("Service match rule must have at least one matcher")
        return self


class ServiceMatchRuleCreateSchema(ServiceMatchRuleBaseSchema):
    """Validate service match rule creation."""


class ServiceMatchRuleUpdateSchema(ServiceMatchRuleBaseSchema):
    """Validate service match rule update."""


class ServiceLinkBaseSchema(ApiModel):
    """Validate service link input."""

    link_type: str = Field(default="other", pattern=SERVICE_LINK_TYPE_PATTERN)
    label: str = Field(
        min_length=NAME_MIN_LENGTH,
        max_length=NAME_MAX_LENGTH,
    )
    url: str = Field(min_length=3, max_length=2048)
    description: str | None = Field(
        default=None,
        max_length=DESCRIPTION_MAX_LENGTH,
    )
    priority: int = Field(default=100, ge=0)
    enabled: bool = True


class ServiceLinkCreateSchema(ServiceLinkBaseSchema):
    """Validate service link creation."""


class ServiceLinkUpdateSchema(ServiceLinkBaseSchema):
    """Validate service link update."""


class ServiceRunbookBaseSchema(ApiModel):
    """Validate service runbook input."""

    title: str = Field(
        min_length=NAME_MIN_LENGTH,
        max_length=NAME_MAX_LENGTH,
    )
    description: str | None = Field(
        default=None,
        max_length=DESCRIPTION_MAX_LENGTH,
    )
    url: str = Field(min_length=3, max_length=2048)
    severity: str | None = Field(default=None, max_length=NAME_MAX_LENGTH)
    matchers: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=100, ge=0)
    enabled: bool = True


class ServiceRunbookCreateSchema(ServiceRunbookBaseSchema):
    """Validate service runbook creation."""


class ServiceRunbookUpdateSchema(ServiceRunbookBaseSchema):
    """Validate service runbook update."""


class ServiceDependencyBaseSchema(ApiModel):
    """Validate service dependency input."""

    depends_on_service_id: int = Field(ge=1)
    dependency_type: str = Field(
        default="hard",
        pattern=SERVICE_DEPENDENCY_TYPE_PATTERN,
    )
    criticality: str = Field(
        default="important",
        pattern=SERVICE_DEPENDENCY_CRITICALITY_PATTERN,
    )
    description: str | None = Field(
        default=None,
        max_length=DESCRIPTION_MAX_LENGTH,
    )
    enabled: bool = True


class ServiceDependencyCreateSchema(ServiceDependencyBaseSchema):
    """Validate service dependency creation."""


class ServiceDependencyUpdateSchema(ServiceDependencyBaseSchema):
    """Validate service dependency update."""
