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


def date_time_property(description, nullable=False):
    """Build an OpenAPI date-time property."""
    schema = {
        "type": "string",
        "format": "date-time",
        "description": description,
    }

    if nullable:
        schema["nullable"] = True

    return schema


def user_short_schema():
    """Build a compact user schema."""
    return {
        "type": "object",
        "nullable": True,
        "properties": {
            "id": {"type": "integer"},
            "username": {"type": "string"},
            "display_name": {"type": "string", "nullable": True},
            "email": {"type": "string", "nullable": True},
            "telegram_user_id": {"type": "string", "nullable": True},
            "slack_user_id": {"type": "string", "nullable": True},
            "mattermost_user_id": {"type": "string", "nullable": True},
        },
    }


def alert_schema(include_payload=False, include_details=False):
    """Build an alert response schema."""
    properties = {
        "id": {"type": "integer"},
        "team_id": {"type": "integer", "nullable": True},
        "team_slug": {"type": "string", "nullable": True},
        "team_name": {"type": "string", "nullable": True},
        "route_id": {"type": "integer", "nullable": True},
        "route_name": {"type": "string", "nullable": True},
        "route_source": {"type": "string", "nullable": True},
        "rotation_id": {"type": "integer", "nullable": True},
        "rotation_name": {"type": "string", "nullable": True},
        "rotation_reminder_interval_seconds": {
            "type": "integer",
            "nullable": True,
            "minimum": 0,
            "description": "Reminder interval in seconds. 0 disables reminders. Otherwise, use 1 minute or more."
        },
        "source": {"type": "string"},
        "external_id": {"type": "string", "nullable": True},
        "dedup_key": {"type": "string"},
        "group_key": {"type": "string"},
        "title": {"type": "string"},
        "message": {"type": "string", "nullable": True},
        "severity": {"type": "string", "nullable": True},
        "status": {"type": "string"},
        "previous_status": {"type": "string", "nullable": True},
        "silenced": {"type": "boolean"},
        "labels": {"type": "object", "additionalProperties": True},
        "labels_count": {"type": "integer"},
        "assignee": {"type": "string", "nullable": True},
        "assignee_id": {"type": "integer", "nullable": True},
        "assignee_details": user_short_schema(),
        "acknowledged_by": {"type": "string", "nullable": True},
        "acknowledged_by_details": user_short_schema(),
        "acknowledged_at": date_time_property("Alert acknowledgement timestamp in UTC.", nullable=True),
        "first_seen_at": date_time_property("First time this alert occurrence was seen in UTC."),
        "last_seen_at": date_time_property("Last time this alert occurrence was seen in UTC."),
        "resolved_at": date_time_property("Time when this alert was resolved in UTC.", nullable=True),
        "last_notification_at": date_time_property("Last notification timestamp in UTC.", nullable=True),
        "reminder_count": {"type": "integer"},
        "escalation_level": {"type": "integer"},
    }

    if include_payload:
        properties["payload"] = {
            "type": "object",
            "nullable": True,
            "additionalProperties": True,
        }

    if include_details:
        properties["events"] = {
            "type": "array",
            "items": {"type": "object", "additionalProperties": True},
        }
        properties["notifications"] = {
            "type": "array",
            "items": {"type": "object", "additionalProperties": True},
        }

    return {
        "type": "object",
        "properties": properties,
    }


def alert_list_schema():
    """Build list alerts response schema."""
    return {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": alert_schema(),
            },
            "pagination": {
                "type": "object",
                "additionalProperties": True,
            },
            "summary": {
                "type": "object",
                "additionalProperties": True,
            },
            "sort": {
                "type": "object",
                "additionalProperties": True,
            },
        },
    }


def tags():
    """
    Return OpenAPI tags.
    """

    return [
        {
            "name": "alerts",
            "description": (
                "Alert lifecycle endpoints. Alerts can be listed, inspected, acknowledged, resolved and audited "
                "through event history."
            ),
        }
    ]


def paths():
    """
    Return OpenAPI paths for alert endpoints.
    """

    return {
        "/api/alerts": {
            "get": {
                "tags": ["alerts"],
                "summary": "List alerts",
                "description": (
                    "Returns alerts with optional filtering and sorting. "
                    "Supports filtering by team, status, source and severity. "
                    "Use sort/order to control table column ordering."
                ),
                "operationId": "listAlerts",
                "parameters": [
                    query_param("team_id", "Filter alerts by team id.", {"type": "integer", "minimum": 1}),
                    query_param("status", "Filter by status: firing, acknowledged, resolved or silenced."),
                    query_param("source", "Filter by source: alertmanager, zabbix or webhook."),
                    query_param("severity", "Filter by severity label or payload value."),
                    query_param(
                        "sort",
                        "Sort field.",
                        {
                            "type": "string",
                            "enum": [
                                "id",
                                "status",
                                "title",
                                "severity",
                                "team",
                                "assignee",
                                "created",
                                "last_seen",
                                "activity",
                                "reminders",
                            ],
                            "default": "activity",
                        },
                    ),
                    query_param(
                        "order",
                        "Sort order.",
                        {
                            "type": "string",
                            "enum": ["asc", "desc"],
                            "default": "desc",
                        },
                    ),
                    query_param("search",
                                "Search by id, title, team, assignee, source, route, rotation or dedup fields."),
                    query_param(
                        "page",
                        "Page number.",
                        {"type": "integer", "minimum": 1, "default": 1},
                    ),
                    query_param(
                        "page_size",
                        "Rows per page. Maximum value is 100.",
                        {"type": "integer", "minimum": 1, "maximum": 100, "default": 25},
                    ),
                    query_param(
                        "sort",
                        "Sort field.",
                        {
                            "type": "string",
                            "enum": [
                                "id",
                                "status",
                                "title",
                                "severity",
                                "team",
                                "assignee",
                                "created",
                                "last_seen",
                                "activity",
                                "reminders",
                            ],
                            "default": "activity",
                        },
                    ),
                    query_param(
                        "order",
                        "Sort order.",
                        {
                            "type": "string",
                            "enum": ["asc", "desc"],
                            "default": "desc",
                        },
                    ),
                ],
                "responses": {"200": response("List of alerts.", alert_list_schema()),},
            }
        },
        "/api/alerts/{alert_id}": {
            "get": {
                "tags": ["alerts"],
                "summary": "Get alert",
                "description": "Returns a single alert with labels, payload, route, team, assignee and status details.",
                "operationId": "getAlert",
                "parameters": [path_param("alert_id", "Alert id.")],
                "responses": {
                    "200": response(
                        "Alert details.",
                        alert_schema(include_payload=True, include_details=True),
                    ),
                    "404": response("Alert not found."),
                },
            }
        },
        "/api/alerts/{alert_id}/ack": {
            "post": {
                "tags": ["alerts"],
                "summary": "Acknowledge alert",
                "description": (
                    "Marks an alert as acknowledged. Once acknowledged, reminder notifications stop for this alert. "
                    "Optionally pass user_id to record who acknowledged it."
                ),
                "operationId": "acknowledgeAlert",
                "parameters": [path_param("alert_id", "Alert id.")],
                "requestBody": json_body(
                    "Optional acknowledge user.",
                    {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "integer", "minimum": 1, "nullable": True},
                        },
                    },
                    required=False,
                ),
                "responses": {
                    "200": response("Alert acknowledged.", alert_schema()),
                    "404": response("Alert not found."),
                },
            }
        },
        "/api/alerts/{alert_id}/resolve": {
            "post": {
                "tags": ["alerts"],
                "summary": "Resolve alert",
                "description": (
                    "Marks an alert as resolved and sends a resolved notification to the route channels. "
                    "Optionally pass user_id to record who resolved it."
                ),
                "operationId": "resolveAlert",
                "parameters": [path_param("alert_id", "Alert id.")],
                "requestBody": json_body(
                    "Optional resolve user.",
                    {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "integer", "minimum": 1, "nullable": True},
                        },
                    },
                    required=False,
                ),
                "responses": {
                    "200": response("Alert resolved.", alert_schema()),
                    "404": response("Alert not found."),
                },
            }
        },
        "/api/alerts/{alert_id}/events": {
            "get": {
                "tags": ["alerts"],
                "summary": "List alert events",
                "description": (
                    "Returns alert history events. This is the main debug endpoint for notifications. "
                    "Failed notifications are stored as notification_failed, reminder_failed or escalation_failed events."
                ),
                "operationId": "listAlertEvents",
                "parameters": [path_param("alert_id", "Alert id.")],
                "responses": {"200": response("Alert event history.")},
            }
        },
    }
