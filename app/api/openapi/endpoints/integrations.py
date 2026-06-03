def path_param(name, description):
    """
    Build an integer path parameter.
    """

    return {
        "name": name,
        "in": "path",
        "required": True,
        "description": description,
        "schema": {"type": "integer", "minimum": 1},
    }


def query_param(name, description, schema=None, required=False):
    """
    Build a query parameter.
    """

    return {
        "name": name,
        "in": "query",
        "required": required,
        "description": description,
        "schema": schema or {"type": "string"},
    }


def json_body(description, schema, required=True):
    """
    Build a JSON request body.
    """

    return {
        "required": required,
        "description": description,
        "content": {
            "application/json": {
                "schema": schema
            }
        },
    }


def response(description, schema=None):
    """
    Build a JSON response.
    """

    item = {"description": description}

    if schema:
        item["content"] = {
            "application/json": {
                "schema": schema
            }
        }

    return item


VOICE_CALLBACK_BODY_SCHEMA = {
    "type": "object",
    "description": (
        "Provider-specific voice callback payload. "
        "IncidentRelay passes this payload to the selected voice provider module. "
        "The provider normalizes it into status, DTMF or error events."
    ),
    "additionalProperties": True,
    "properties": {
        "call_id": {
            "type": "string",
            "description": "External provider call id.",
            "example": "abc-123",
        },
        "event": {
            "type": "string",
            "description": "Provider event name.",
            "example": "dtmf",
        },
        "event_type": {
            "type": "string",
            "description": "Normalized or provider-specific event type.",
            "enum": ["status", "dtmf", "error"],
            "example": "dtmf",
        },
        "status": {
            "type": "string",
            "description": "Provider call status.",
            "example": "answered",
        },
        "digit": {
            "type": "string",
            "description": "DTMF digit pressed by the call recipient.",
            "example": "1",
        },
        "action": {
            "type": "string",
            "description": (
                "Optional normalized action. "
                "If omitted, IncidentRelay maps digit through channel config dtmf_actions."
            ),
            "enum": ["acknowledge", "resolve"],
            "example": "acknowledge",
        },
        "alert_id": {
            "type": "integer",
            "nullable": True,
            "description": "Optional alert id returned by the provider.",
            "example": 123,
        },
        "message": {
            "type": "string",
            "nullable": True,
            "description": "Optional provider event message.",
            "example": "User pressed 1",
        },
    },
    "example": {
        "call_id": "abc-123",
        "event_type": "dtmf",
        "status": "answered",
        "digit": "1",
    },
}


VOICE_CALLBACK_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "example": "processed",
        },
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "call_id": {
                        "type": "string",
                        "example": "abc-123",
                    },
                    "event_type": {
                        "type": "string",
                        "example": "dtmf",
                    },
                    "status": {
                        "type": "string",
                        "nullable": True,
                        "example": "answered",
                    },
                    "digit": {
                        "type": "string",
                        "nullable": True,
                        "example": "1",
                    },
                    "action": {
                        "type": "string",
                        "nullable": True,
                        "example": "acknowledge",
                    },
                    "alert_id": {
                        "type": "integer",
                        "nullable": True,
                        "example": 123,
                    },
                },
            },
        },
    },
}


def tags():
    """
    Return OpenAPI tags.
    """

    return [
        {
            "name": "integrations",
            "description": (
                "Incoming alert endpoints for Alertmanager, Zabbix and generic webhooks. "
                "Each endpoint requires a route intake token. The route token selects "
                "the route, team, rotation and notification channels."
            ),
        }
    ]


def paths():
    """
    Return OpenAPI paths for integration endpoints.
    """

    alertmanager_alert_schema = {
        "type": "object",
        "required": ["labels"],
        "additionalProperties": True,
        "properties": {
            "status": {
                "type": "string",
                "enum": ["firing", "resolved"],
                "default": "firing",
                "description": "Alert status from Alertmanager.",
            },
            "labels": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": "Alert labels.",
                "example": {
                    "alertname": "TargetMissingOrDown",
                    "instance": "10.101.164.165:9290",
                    "severity": "critical",
                    "team": "infra",
                },
            },
            "annotations": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": "Alert annotations.",
                "example": {
                    "summary": "Target missing or down",
                    "description": "Target 10.101.164.165:9290 is not available",
                },
            },
            "startsAt": {
                "type": "string",
                "format": "date-time",
                "nullable": True,
                "description": "Alert start time.",
            },
            "endsAt": {
                "type": "string",
                "format": "date-time",
                "nullable": True,
                "description": "Alert end time.",
            },
            "generatorURL": {
                "type": "string",
                "nullable": True,
                "description": "URL to the source that generated the alert.",
            },
            "fingerprint": {
                "type": "string",
                "nullable": True,
                "description": "Alertmanager alert fingerprint. Used for deduplication when available.",
                "example": "target-missing-10.101.164.165",
            },
            "silenceURL": {
                "type": "string",
                "nullable": True,
                "description": "Alertmanager silence URL.",
                "example": "https://alertmanager.example.com/#/silences/new",
            },
            "dashboardURL": {
                "type": "string",
                "nullable": True,
                "description": "Dashboard URL related to this alert.",
                "example": "https://grafana.example.com/d/node",
            },
            "panelURL": {
                "type": "string",
                "nullable": True,
                "description": "Panel URL related to this alert.",
                "example": "https://grafana.example.com/d/node?viewPanel=12",
            },
        },
    }

    alertmanager_body = {
        "type": "object",
        "required": ["alerts"],
        "additionalProperties": True,
        "properties": {
            "receiver": {
                "type": "string",
                "nullable": True,
                "description": "Alertmanager receiver name.",
                "example": "incidentrelay-infra",
            },
            "status": {
                "type": "string",
                "enum": ["firing", "resolved"],
                "default": "firing",
                "description": "Overall payload status.",
            },
            "alerts": {
                "type": "array",
                "description": "Alerts included in the Alertmanager notification.",
                "items": alertmanager_alert_schema,
            },
            "groupLabels": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": "Alertmanager groupLabels field.",
                "example": {
                    "alertname": "TargetMissingOrDown",
                    "instance": "10.101.164.165:9290",
                },
            },
            "commonLabels": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": "Alertmanager commonLabels field.",
                "example": {
                    "alertname": "TargetMissingOrDown",
                    "severity": "critical",
                    "team": "infra",
                },
            },
            "commonAnnotations": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": "Alertmanager commonAnnotations field.",
                "example": {
                    "summary": "Target missing or down",
                    "event_link": "https://grafana.example.com/d/node?viewPanel=12",
                    "runbook_url": "https://wiki.example.com/runbooks/disk-full",
                },
            },
            "externalURL": {
                "type": "string",
                "nullable": True,
                "description": "Alertmanager external URL.",
                "example": "https://alertmanager.example.com",
            },
            "version": {
                "type": "string",
                "nullable": True,
                "description": "Alertmanager webhook payload version.",
                "example": "4",
            },
            "groupKey": {
                "type": "string",
                "nullable": True,
                "description": "Alertmanager group key.",
                "example": '{}/{severity="critical"}:{alertname="TargetMissingOrDown"}',
            },
            "truncatedAlerts": {
                "type": "integer",
                "nullable": True,
                "description": "Number of truncated alerts.",
                "example": 0,
            },
        },
        "example": {
            "receiver": "incidentrelay-infra",
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "TargetMissingOrDown",
                        "instance": "10.101.164.165:9290",
                        "severity": "critical",
                        "team": "infra",
                    },
                    "annotations": {
                        "summary": "Target missing or down",
                        "description": "Target 10.101.164.165:9290 is not available",
                    },
                    "startsAt": "2026-04-28T15:35:00Z",
                    "endsAt": "0001-01-01T00:00:00Z",
                    "generatorURL": "https://prometheus.example.com/graph?g0.expr=up",
                    "fingerprint": "target-missing-10.101.164.165",
                }
            ],
            "groupLabels": {
                "alertname": "TargetMissingOrDown",
                "instance": "10.101.164.165:9290",
            },
            "commonLabels": {
                "severity": "critical",
                "team": "infra",
            },
            "commonAnnotations": {
                "summary": "Target missing or down",
            },
            "externalURL": "https://alertmanager.example.com",
            "version": "4",
            "groupKey": '{}/{severity="critical"}:{alertname="TargetMissingOrDown"}',
            "truncatedAlerts": 0,
        },
    }

    zabbix_body = {
        "type": "object",
        "additionalProperties": True,
        "properties": {
            "event_id": {
                "type": "string",
                "description": "Zabbix event id. Use the same event_id for firing and resolved events.",
                "example": "100500",
            },
            "trigger_id": {
                "type": "string",
                "nullable": True,
                "description": "Zabbix trigger id.",
                "example": "200600",
            },
            "title": {
                "type": "string",
                "nullable": True,
                "description": "Alert title.",
                "example": "Disk space is low",
            },
            "host": {
                "type": "string",
                "nullable": True,
                "description": "Zabbix host name.",
                "example": "host1",
            },
            "trigger": {
                "type": "string",
                "nullable": True,
                "description": "Zabbix trigger name.",
                "example": "DiskSpaceLow",
            },
            "message": {
                "type": "string",
                "nullable": True,
                "description": "Alert message.",
                "example": "/var is 95% full",
            },
            "severity": {
                "type": "string",
                "nullable": True,
                "description": "Alert severity.",
                "example": "high",
            },
            "status": {
                "type": "string",
                "enum": ["firing", "resolved"],
                "default": "firing",
                "description": "Alert status.",
            },
            "team": {
                "type": "string",
                "nullable": True,
                "description": "Optional team slug fallback.",
                "example": "infra",
            },
            "labels": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": "Additional labels.",
                "example": {
                    "team": "infra",
                    "host": "host1",
                    "trigger": "DiskSpaceLow",
                },
            },
            "fingerprint": {
                "type": "string",
                "nullable": True,
                "description": "Optional stable deduplication key.",
                "example": "zabbix-100500",
            },
            "event_name": {
                "type": "string",
                "nullable": True,
                "description": "Zabbix event name, usually {EVENT.NAME}.",
                "example": "Disk space is low on host1",
            },
            "problem_name": {
                "type": "string",
                "nullable": True,
                "description": "Problem name fallback.",
                "example": "Disk space is low on host1",
            },
            "trigger_name": {
                "type": "string",
                "nullable": True,
                "description": "Zabbix trigger name.",
                "example": "Free disk space is less than 10%",
            },
            "event_tag": {
                "nullable": True,
                "description": "Zabbix event tags, for example {EVENT.TAGS} or {EVENT.TAGSJSON}.",
                "example": "team: infra, service: filesystem",
            },
            "tags": {
                "nullable": True,
                "description": "Zabbix tags. Can be object, array, JSON string or EVENT.TAGSJSON.",
                "example": [
                    {"tag": "team", "value": "infra"},
                    {"tag": "service", "value": "filesystem"}
                ],
            },
            "event_link": {
                "type": "string",
                "nullable": True,
                "description": "Direct URL to the Zabbix event/problem.",
                "example": "https://zabbix.example.com/tr_events.php?triggerid=98765&eventid=123456",
            },
            "event_url": {
                "type": "string",
                "nullable": True,
                "description": "Alias for event_link.",
            },
            "problem_url": {
                "type": "string",
                "nullable": True,
                "description": "Alias for event_link.",
            },
            "trigger_url": {
                "type": "string",
                "nullable": True,
                "description": "Alias for event_link.",
            },
            "zabbix_url": {
                "type": "string",
                "nullable": True,
                "description": "Base Zabbix frontend URL. IncidentRelay can build event_link from it when event_id is present.",
                "example": "https://zabbix.example.com",
            },
        },
        "example": {
            "status": "firing",
            "event_id": "123456",
            "trigger_id": "98765",
            "event_name": "High CPU load on host1",
            "host": "host1",
            "event_severity": "High",
            "event_status": "PROBLEM",
            "opdata": "CPU load is above 90%",
            "event_tag": "team: infra, service: cpu",
            "event_link": "https://zabbix.example.com/tr_events.php?triggerid=98765&eventid=123456",
            "team": "infra",
            "labels": {
                "host": "host1",
                "service": "cpu",
                "environment": "prod"
            }
        }
    }

    webhook_body = {
        "type": "object",
        "required": ["title"],
        "additionalProperties": True,
        "properties": {
            "title": {
                "type": "string",
                "description": "Alert title.",
                "example": "Disk is full",
            },
            "message": {
                "type": "string",
                "nullable": True,
                "description": "Alert message.",
                "example": "/var is 95% full",
            },
            "severity": {
                "type": "string",
                "nullable": True,
                "description": "Alert severity.",
                "example": "critical",
            },
            "status": {
                "type": "string",
                "enum": ["firing", "resolved"],
                "default": "firing",
                "description": "Alert status.",
            },
            "team": {
                "type": "string",
                "nullable": True,
                "description": "Optional team slug fallback.",
                "example": "infra",
            },
            "labels": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": "Alert labels.",
                "example": {
                    "team": "infra",
                    "instance": "host1",
                    "alertname": "DiskFull",
                },
            },
            "fingerprint": {
                "type": "string",
                "nullable": True,
                "description": "Stable deduplication key. Use the same value for firing and resolved.",
                "example": "disk-full-host1-var",
            },
            "external_id": {
                "type": "string",
                "nullable": True,
                "description": "External system event id.",
                "example": "event-123",
            },
            "event_link": {
                "type": "string",
                "nullable": True,
                "description": "Direct URL to the source event.",
                "example": "https://monitoring.example.com/events/deploy-incident-42",
            },
            "event_url": {
                "type": "string",
                "nullable": True,
                "description": "Alias for event_link.",
            },
            "alert_url": {
                "type": "string",
                "nullable": True,
                "description": "Alias for event_link.",
            },
            "source_url": {
                "type": "string",
                "nullable": True,
                "description": "Alias for event_link.",
            },
            "dashboard_url": {
                "type": "string",
                "nullable": True,
                "description": "Dashboard URL related to the alert.",
            },
            "runbook_url": {
                "type": "string",
                "nullable": True,
                "description": "Runbook URL related to the alert.",
            },
        },
        "example": {
            "title": "Disk is full",
            "message": "/var is 95% full",
            "severity": "critical",
            "status": "firing",
            "fingerprint": "disk-full-host1-var",
            "labels": {
                "team": "infra",
                "instance": "host1",
                "alertname": "DiskFull",
            },
            "event_link": "https://monitoring.example.com/events/deploy-incident-42",
        },
    }

    return {
        "/api/integrations/alertmanager": {
            "post": {
                "tags": ["integrations"],
                "summary": "Receive Alertmanager alerts",
                "description": (
                    "Accepts the standard Prometheus Alertmanager webhook payload. "
                    "The route intake token must belong to a route with source=alertmanager. "
                    "Top-level Alertmanager fields such as receiver, groupLabels, commonLabels, "
                    "commonAnnotations, externalURL, version, groupKey and truncatedAlerts are accepted."
                ),
                "operationId": "receiveAlertmanagerAlerts",
                "security": [{"bearerAuth": []}],
                "requestBody": json_body("Standard Alertmanager webhook payload.", alertmanager_body),
                "responses": {
                    "200": response("Alerts accepted."),
                    "400": response("Invalid Alertmanager payload."),
                    "401": response("Route intake token or API token is required."),
                },
            }
        },
        "/api/integrations/zabbix": {
            "post": {
                "tags": ["integrations"],
                "summary": "Receive Zabbix alerts",
                "description": (
                    "Receives a Zabbix webhook payload. The route intake token must belong "
                    "to a route with source=zabbix. Use the same event_id for firing and resolved events."
                ),
                "operationId": "receiveZabbixAlerts",
                "security": [{"bearerAuth": []}],
                "requestBody": json_body("Zabbix webhook payload.", zabbix_body),
                "responses": {
                    "200": response("Alert accepted."),
                    "400": response("Invalid Zabbix payload."),
                    "401": response("Route intake token or API token is required."),
                },
            }
        },
        "/api/integrations/webhook": {
            "post": {
                "tags": ["integrations"],
                "summary": "Receive generic webhook alerts",
                "description": (
                    "Receives a generic alert payload. The route intake token must belong "
                    "to a route with source=webhook. Provide a stable fingerprint to avoid duplicate alerts."
                ),
                "operationId": "receiveGenericWebhookAlerts",
                "security": [{"bearerAuth": []}],
                "requestBody": json_body("Generic webhook payload.", webhook_body),
                "responses": {
                    "200": response("Alert accepted."),
                    "400": response("Invalid webhook payload."),
                    "401": response("Route intake token or API token is required."),
                },
            }
        },
        "/api/integrations/mattermost/actions": {
            "post": {
                "tags": ["integrations"],
                "summary": "Handle Mattermost interactive buttons",
                "description": (
                    "Receives Mattermost interactive message button callbacks. The endpoint validates "
                    "the callback secret from the action context, acknowledges or resolves the alert, "
                    "and updates the original Mattermost post when the channel is configured in Bot API mode."
                ),
                "operationId": "handleMattermostAction",
                "requestBody": json_body("Mattermost interactive action payload.", {
                    "type": "object",
                    "properties": {
                        "context": {
                            "type": "object",
                            "properties": {
                                "alert_id": {"type": "integer"},
                                "channel_id": {"type": "integer"},
                                "action": {"type": "string", "enum": ["acknowledge", "resolve"]},
                                "secret": {"type": "string"},
                            },
                        }
                    },
                }),
                "responses": {
                    "200": response("Action processed."),
                    "400": response("Invalid action payload."),
                    "403": response("Invalid callback secret."),
                },
            }
        },
        "/api/integrations/voice/callback/{channel_id}/{secret}": {
            "post": {
                "tags": ["integrations"],
                "summary": "Handle voice provider callback",
                "description": (
                    "Receives callbacks from voice call providers. "
                    "The endpoint validates the channel callback secret, loads the provider "
                    "configured for the voice_call channel, and passes the raw payload to "
                    "provider.parse_callback(). "
                    "Providers may normalize call status changes, DTMF button presses and errors. "
                    "DTMF digits can be mapped to IncidentRelay actions through channel config, "
                    "for example 1=acknowledge and 2=resolve."
                ),
                "operationId": "handleVoiceProviderCallback",
                "parameters": [
                    path_param("channel_id", "Voice call notification channel id."),
                    {
                        "name": "secret",
                        "in": "path",
                        "required": True,
                        "description": (
                            "Voice callback secret. "
                            "Uses channel config callback_secret or global voice.callback_secret."
                        ),
                        "schema": {
                            "type": "string",
                            "minLength": 1,
                        },
                    },
                ],
                "requestBody": json_body(
                    "Provider-specific callback payload.",
                    VOICE_CALLBACK_BODY_SCHEMA,
                ),
                "responses": {
                    "200": response(
                        "Callback processed or ignored.",
                        VOICE_CALLBACK_RESPONSE_SCHEMA,
                    ),
                    "400": response(
                        "Invalid callback payload, provider parse error or channel is not voice_call."
                    ),
                    "403": response("Invalid voice callback secret."),
                    "404": response("Channel or notification not found."),
                },
            }
        },
    }
