from typing import Any, Dict, List

from pydantic import ConfigDict, Field, model_validator

from app.api.schemas.base import ApiModel


class AlertmanagerAlertSchema(ApiModel):
    """
    Validate one Alertmanager alert.
    """

    model_config = ConfigDict(extra="ignore")

    status: str = "firing"
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    startsAt: str | None = None
    endsAt: str | None = None
    generatorURL: str | None = None
    fingerprint: str | None = None


class AlertmanagerWebhookSchema(ApiModel):
    """
    Validate Alertmanager webhook payload.
    """

    model_config = ConfigDict(extra="ignore")

    receiver: str | None = None
    status: str = "firing"
    alerts: list[AlertmanagerAlertSchema]
    groupLabels: dict[str, str] = Field(default_factory=dict)
    commonLabels: dict[str, str] = Field(default_factory=dict)
    commonAnnotations: dict[str, str] = Field(default_factory=dict)
    externalURL: str | None = None
    version: str | None = None
    groupKey: str | None = None
    truncatedAlerts: int | None = None
    generatorURL: str | None = None
    silenceURL: str | None = None
    dashboardURL: str | None = None
    panelURL: str | None = None


class ZabbixWebhookSchema(ApiModel):
    """Validate Zabbix webhook payload at envelope level."""

    # Zabbix media types are often customized with additional macro fields.
    # Keep known fields typed, but allow extra parameters to pass through
    # to the normalizer.
    model_config = ConfigDict(extra="allow")

    event_id: str | None = None
    eventid: str | None = None

    trigger_id: str | None = None
    triggerid: str | None = None

    title: str | None = None
    subject: str | None = None
    name: str | None = None
    event_name: str | None = None
    trigger_name: str | None = None
    problem_name: str | None = None

    message: str | None = None
    description: str | None = None
    opdata: str | None = None

    severity: str | None = None
    event_severity: str | None = None
    trigger_severity: str | None = None

    status: str | None = None
    event_status: str | None = None

    team: str | None = None

    host: str | None = None
    host_name: str | None = None
    hostname: str | None = None

    labels: Dict[str, Any] = Field(default_factory=dict)

    # Can be a dict, a Zabbix EVENT.TAGSJSON array, or sometimes a raw string.
    tags: Any = None
    event_tag: Any = None
    event_tags: Any = None
    tags_json: Any = None

    fingerprint: str | None = None

    event_link: str | None = None
    event_url: str | None = None
    problem_url: str | None = None
    trigger_url: str | None = None
    zabbix_url: str | None = None

    @model_validator(mode="after")
    def validate_not_empty(self):
        has_identity = bool(
            self.event_id
            or self.eventid
            or self.trigger_id
            or self.triggerid
            or self.fingerprint
        )

        has_content = bool(
            self.title
            or self.subject
            or self.name
            or self.event_name
            or self.trigger_name
            or self.problem_name
            or self.message
            or self.description
            or self.opdata
            or self.event_link
            or self.event_url
            or self.problem_url
            or self.trigger_url
        )

        has_labels = bool(self.labels or self.tags)

        if not (has_identity or has_content or has_labels):
            raise ValueError(
                "Zabbix webhook payload must contain at least one of: "
                "event_id, trigger_id, fingerprint, title, subject, "
                "event_name, trigger_name, problem_name, message, description, "
                "opdata, labels or tags"
            )

        return self


class GenericWebhookSchema(ApiModel):
    """
    Validate generic webhook payload.
    """

    model_config = ConfigDict(extra="ignore")

    title: str = Field(min_length=1, max_length=255)
    message: str | None = None
    severity: str | None = None
    status: str | None = None
    team: str | None = None
    labels: Dict[str, Any] = Field(default_factory=dict)
    fingerprint: str | None = None
    external_id: str | None = None

    event_link: str | None = None
    event_url: str | None = None
    alert_url: str | None = None
    source_url: str | None = None
    dashboard_url: str | None = None
    runbook_url: str | None = None
