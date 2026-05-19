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


class ZabbixWebhookSchema(ApiModel):
    """
    Validate Zabbix webhook payload at envelope level.
    """

    event_id: str | None = None
    trigger_id: str | None = None
    title: str | None = None
    subject: str | None = None
    message: str | None = None
    severity: str | None = None
    status: str | None = None
    team: str | None = None
    labels: Dict[str, Any] = Field(default_factory=dict)
    fingerprint: str | None = None

    @model_validator(mode="after")
    def validate_not_empty(self):
        has_identity = bool(self.event_id or self.trigger_id or self.fingerprint)
        has_content = bool(self.title or self.subject or self.message)
        has_labels = bool(self.labels)

        if not (has_identity or has_content or has_labels):
            raise ValueError(
                "Zabbix webhook payload must contain at least one of: "
                "event_id, trigger_id, fingerprint, title, subject, message or labels"
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
