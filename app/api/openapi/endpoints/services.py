from app.api.schemas.limits import (
    DESCRIPTION_MAX_LENGTH,
    NAME_MAX_LENGTH,
    NAME_MIN_LENGTH,
    SLUG_MAX_LENGTH,
    SLUG_MIN_LENGTH,
)


SERVICE_TYPES = [
    "api",
    "web",
    "database",
    "queue",
    "cache",
    "worker",
    "cron",
    "network",
    "storage",
    "infrastructure",
    "external",
    "other",
]

SERVICE_ENVIRONMENTS = [
    "production",
    "staging",
    "development",
    "testing",
    "shared",
]

SERVICE_CRITICALITIES = [
    "low",
    "medium",
    "high",
    "critical",
]

SERVICE_TIERS = [
    "tier_1",
    "tier_2",
    "tier_3",
    "tier_4",
]

SERVICE_STATUSES = [
    "operational",
    "degraded",
    "partial_outage",
    "major_outage",
    "maintenance",
    "disabled",
    "unknown",
]

SERVICE_STATUS_SOURCES = [
    "manual",
    "alerts",
    "maintenance",
    "system",
]

SERVICE_LINK_TYPES = [
    "dashboard",
    "metrics",
    "logs",
    "traces",
    "repository",
    "documentation",
    "status_page",
    "wiki",
    "other",
]

SERVICE_DEPENDENCY_TYPES = [
    "hard",
    "soft",
    "external",
    "informational",
]

SERVICE_DEPENDENCY_CRITICALITIES = [
    "required",
    "important",
    "optional",
]


def path_param(name, description):
    """Build an integer path parameter."""
    return {
        "name": name,
        "in": "path",
        "required": True,
        "description": description,
        "schema": {"type": "integer", "minimum": 1},
    }


def query_param(name, description, schema=None, required=False):
    """Build a query parameter."""
    return {
        "name": name,
        "in": "query",
        "required": required,
        "description": description,
        "schema": schema or {"type": "string"},
    }


def json_body(description, schema, required=True):
    """Build a JSON request body."""
    return {
        "required": required,
        "description": description,
        "content": {
            "application/json": {
                "schema": schema,
            },
        },
    }


def response(description, schema=None):
    """Build a JSON response."""
    item = {"description": description}
    if schema:
        item["content"] = {
            "application/json": {
                "schema": schema,
            },
        }
    return item


ERROR_SCHEMA = {
    "type": "object",
    "properties": {
        "error": {"type": "string", "example": "validation_error"},
        "message": {"type": "string", "nullable": True},
    },
}


DELETE_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "deleted": {"type": "boolean", "example": True},
        "id": {"type": "integer", "example": 1},
    },
}


SERVICE_SCHEMA = {
    "type": "object",
    "required": ["team_id", "slug", "name"],
    "additionalProperties": False,
    "properties": {
        "id": {"type": "integer", "readOnly": True},
        "group_id": {
            "type": "integer",
            "readOnly": True,
            "description": "Owner group id inherited from the service team.",
        },
        "team_id": {
            "type": "integer",
            "minimum": 1,
            "description": "Owner team id.",
            "example": 1,
        },
        "team_name": {"type": "string", "nullable": True, "readOnly": True},
        "team_slug": {"type": "string", "nullable": True, "readOnly": True},
        "slug": {
            "type": "string",
            "minLength": SLUG_MIN_LENGTH,
            "maxLength": SLUG_MAX_LENGTH,
            "pattern": "^[a-z0-9][a-z0-9-]*$",
            "description": "Stable service identifier used by API/UI.",
            "example": "rabbitmq-cloud",
        },
        "name": {
            "type": "string",
            "minLength": NAME_MIN_LENGTH,
            "maxLength": NAME_MAX_LENGTH,
            "example": "RabbitMQ Cloud",
        },
        "description": {
            "type": "string",
            "nullable": True,
            "maxLength": DESCRIPTION_MAX_LENGTH,
            "example": "Shared RabbitMQ cluster used by production services.",
        },
        "service_type": {
            "type": "string",
            "enum": SERVICE_TYPES,
            "default": "other",
            "example": "queue",
        },
        "environment": {
            "type": "string",
            "enum": SERVICE_ENVIRONMENTS,
            "default": "production",
        },
        "criticality": {
            "type": "string",
            "enum": SERVICE_CRITICALITIES,
            "default": "medium",
        },
        "tier": {
            "type": "string",
            "enum": SERVICE_TIERS,
            "default": "tier_3",
        },
        "status": {
            "type": "string",
            "enum": SERVICE_STATUSES,
            "default": "operational",
        },
        "status_source": {
            "type": "string",
            "enum": SERVICE_STATUS_SOURCES,
            "default": "manual",
        },
        "status_message": {
            "type": "string",
            "nullable": True,
            "maxLength": DESCRIPTION_MAX_LENGTH,
        },
        "default_rotation_id": {
            "type": "integer",
            "nullable": True,
            "minimum": 1,
            "description": "Default rotation for this service. Must belong to service team.",
        },
        "default_escalation_policy_id": {
            "type": "integer",
            "nullable": True,
            "minimum": 1,
            "description": "Default escalation policy for this service. Must belong to service team.",
        },
        "labels": {
            "type": "object",
            "additionalProperties": True,
            "default": {},
            "example": {"system": "messaging", "owner": "infra"},
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "default": [],
            "example": ["rabbitmq", "production"],
        },
        "metadata": {
            "type": "object",
            "additionalProperties": True,
            "default": {},
        },
        "enabled": {"type": "boolean", "default": True},
        "public": {
            "type": "boolean",
            "default": False,
            "description": "Whether the service can be exposed on status-page style views.",
        },
        "public_name": {
            "type": "string",
            "nullable": True,
            "minLength": NAME_MIN_LENGTH,
            "maxLength": NAME_MAX_LENGTH,
        },
        "public_description": {
            "type": "string",
            "nullable": True,
            "maxLength": DESCRIPTION_MAX_LENGTH,
        },
        "public_order": {
            "type": "integer",
            "minimum": 0,
            "default": 100,
        },
    },
}


SERVICE_MATCH_RULE_SCHEMA = {
    "type": "object",
    "required": ["team_id", "service_id", "name", "matchers"],
    "additionalProperties": False,
    "properties": {
        "id": {"type": "integer", "readOnly": True},
        "team_id": {"type": "integer", "minimum": 1},
        "route_id": {
            "type": "integer",
            "minimum": 1,
            "nullable": True,
            "description": "Optional route scope. When null, the rule can match all routes in the team.",
        },
        "route_name": {"type": "string", "nullable": True, "readOnly": True},
        "service_id": {"type": "integer", "minimum": 1},
        "service_name": {"type": "string", "nullable": True, "readOnly": True},
        "position": {
            "type": "integer",
            "minimum": 0,
            "default": 0,
            "description": "Lower position is evaluated first.",
        },
        "name": {
            "type": "string",
            "minLength": NAME_MIN_LENGTH,
            "maxLength": NAME_MAX_LENGTH,
            "example": "RabbitMQ labels",
        },
        "description": {
            "type": "string",
            "nullable": True,
            "maxLength": DESCRIPTION_MAX_LENGTH,
        },
        "matchers": {
            "type": "object",
            "additionalProperties": True,
            "description": "Matcher object evaluated against incoming alert labels/annotations/payload.",
            "example": {
                "labels": {
                    "job": "RabbitMQ",
                    "rabbitmq": {
                        "op": "regex",
                        "value": "^rabbitmq-cloud$",
                    },
                },
            },
        },
        "enabled": {"type": "boolean", "default": True},
    },
}


SERVICE_LINK_SCHEMA = {
    "type": "object",
    "required": ["label", "url"],
    "additionalProperties": False,
    "properties": {
        "id": {"type": "integer", "readOnly": True},
        "service_id": {"type": "integer", "readOnly": True},
        "link_type": {
            "type": "string",
            "enum": SERVICE_LINK_TYPES,
            "default": "other",
            "example": "dashboard",
        },
        "label": {
            "type": "string",
            "minLength": NAME_MIN_LENGTH,
            "maxLength": NAME_MAX_LENGTH,
            "example": "Grafana dashboard",
        },
        "url": {
            "type": "string",
            "minLength": 3,
            "maxLength": 2048,
            "example": "https://grafana.example.com/d/rabbitmq-cloud",
        },
        "description": {
            "type": "string",
            "nullable": True,
            "maxLength": DESCRIPTION_MAX_LENGTH,
        },
        "priority": {"type": "integer", "minimum": 0, "default": 100},
        "enabled": {"type": "boolean", "default": True},
    },
}


SERVICE_RUNBOOK_SCHEMA = {
    "type": "object",
    "required": ["title", "url"],
    "additionalProperties": False,
    "properties": {
        "id": {"type": "integer", "readOnly": True},
        "service_id": {"type": "integer", "readOnly": True},
        "title": {
            "type": "string",
            "minLength": NAME_MIN_LENGTH,
            "maxLength": NAME_MAX_LENGTH,
            "example": "RabbitMQ cluster partition",
        },
        "description": {
            "type": "string",
            "nullable": True,
            "maxLength": DESCRIPTION_MAX_LENGTH,
        },
        "url": {
            "type": "string",
            "minLength": 3,
            "maxLength": 2048,
            "example": "https://docs.example.com/runbooks/rabbitmq/cluster-partition",
        },
        "severity": {
            "type": "string",
            "nullable": True,
            "maxLength": NAME_MAX_LENGTH,
            "example": "critical",
        },
        "matchers": {
            "type": "object",
            "additionalProperties": True,
            "default": {},
            "description": "Optional matcher object used to select a more specific runbook.",
            "example": {"labels": {"alertname": "RabbitMQClusterPartition"}},
        },
        "priority": {"type": "integer", "minimum": 0, "default": 100},
        "enabled": {"type": "boolean", "default": True},
    },
}


SERVICE_DEPENDENCY_SCHEMA = {
    "type": "object",
    "required": ["depends_on_service_id"],
    "additionalProperties": False,
    "properties": {
        "id": {"type": "integer", "readOnly": True},
        "service_id": {"type": "integer", "readOnly": True},
        "depends_on_service_id": {
            "type": "integer",
            "minimum": 1,
            "description": "Upstream service id.",
        },
        "depends_on_service_name": {
            "type": "string",
            "nullable": True,
            "readOnly": True,
        },
        "depends_on_service_slug": {
            "type": "string",
            "nullable": True,
            "readOnly": True,
        },
        "dependency_type": {
            "type": "string",
            "enum": SERVICE_DEPENDENCY_TYPES,
            "default": "hard",
        },
        "criticality": {
            "type": "string",
            "enum": SERVICE_DEPENDENCY_CRITICALITIES,
            "default": "important",
        },
        "description": {
            "type": "string",
            "nullable": True,
            "maxLength": DESCRIPTION_MAX_LENGTH,
        },
        "enabled": {"type": "boolean", "default": True},
    },
}


SERVICE_ANALYTICS_SCHEMA = {
    "type": "object",
    "properties": {
        "service_id": {"type": "integer"},
        "service_name": {"type": "string"},
        "service_slug": {"type": "string"},
        "team_id": {"type": "integer"},
        "team_name": {"type": "string", "nullable": True},
        "team_slug": {"type": "string", "nullable": True},
        "service_status": {"type": "string", "enum": SERVICE_STATUSES},
        "service_criticality": {"type": "string", "enum": SERVICE_CRITICALITIES},
        "service_environment": {"type": "string", "enum": SERVICE_ENVIRONMENTS},
        "service_tier": {"type": "string", "enum": SERVICE_TIERS},
        "total_alerts": {"type": "integer"},
        "open_alerts": {"type": "integer"},
        "firing_alerts": {"type": "integer"},
        "acknowledged_alerts": {"type": "integer"},
        "resolved_alerts": {"type": "integer"},
        "silenced_alerts": {"type": "integer"},
        "critical_open_alerts": {"type": "integer"},
        "warning_open_alerts": {"type": "integer"},
        "last_alert_at": {
            "type": "string",
            "format": "date-time",
            "nullable": True,
        },
    },
}


SERVICE_IMPACT_SCHEMA = {
    "type": "object",
    "properties": {
        "service_id": {"type": "integer"},
        "service_name": {"type": "string"},
        "service_slug": {"type": "string"},
        "team_id": {"type": "integer"},
        "team_name": {"type": "string", "nullable": True},
        "team_slug": {"type": "string", "nullable": True},
        "own_status": {"type": "string", "enum": SERVICE_STATUSES},
        "alert_impact_status": {"type": "string", "enum": SERVICE_STATUSES},
        "dependency_impact_status": {"type": "string", "enum": SERVICE_STATUSES},
        "effective_status": {"type": "string", "enum": SERVICE_STATUSES},
        "has_alert_impact": {"type": "boolean"},
        "has_dependency_impact": {"type": "boolean"},
        "open_alerts": {"type": "integer"},
        "critical_open_alerts": {"type": "integer"},
        "warning_open_alerts": {"type": "integer"},
        "upstream_issues_count": {"type": "integer"},
        "upstream_issues": {
            "type": "array",
            "items": {"type": "object"},
        },
        "criticality": {"type": "string", "enum": SERVICE_CRITICALITIES},
        "environment": {"type": "string", "enum": SERVICE_ENVIRONMENTS},
        "tier": {"type": "string", "enum": SERVICE_TIERS},
        "enabled": {"type": "boolean"},
    },
}


def tags():
    """Return OpenAPI tags."""
    return [
        {
            "name": "services",
            "description": (
                "Service directory and affected-system model. "
                "Services group alerts by the logical system that is broken, "
                "can be linked to routes, matched by alert labels, and can expose "
                "runbooks, links, dependencies, analytics and impact status."
            ),
        }
    ]


def paths():
    """Return OpenAPI paths for service endpoints."""
    return {
        "/api/services": {
            "get": {
                "tags": ["services"],
                "summary": "List services",
                "description": (
                    "Returns services visible to the current user. "
                    "Optional team_id filters services by team."
                ),
                "operationId": "listServices",
                "parameters": [
                    query_param(
                        "team_id",
                        "Filter services by team id.",
                        {"type": "integer", "minimum": 1},
                    )
                ],
                "responses": {
                    "200": response(
                        "List of services.",
                        {"type": "array", "items": SERVICE_SCHEMA},
                    ),
                    "403": response("Access denied.", ERROR_SCHEMA),
                },
            },
            "post": {
                "tags": ["services"],
                "summary": "Create service",
                "description": (
                    "Creates a logical service under a team. "
                    "Team write access is required."
                ),
                "operationId": "createService",
                "requestBody": json_body("Service properties.", SERVICE_SCHEMA),
                "responses": {
                    "201": response("Service created.", SERVICE_SCHEMA),
                    "400": response("Validation error.", ERROR_SCHEMA),
                    "403": response("Access denied.", ERROR_SCHEMA),
                },
            },
        },
        "/api/services/{service_id}": {
            "get": {
                "tags": ["services"],
                "summary": "Get service",
                "description": "Returns one service by id.",
                "operationId": "getService",
                "parameters": [path_param("service_id", "Service id.")],
                "responses": {
                    "200": response("Service details.", SERVICE_SCHEMA),
                    "403": response("Access denied.", ERROR_SCHEMA),
                    "404": response("Service not found.", ERROR_SCHEMA),
                },
            },
            "put": {
                "tags": ["services"],
                "summary": "Update service",
                "description": (
                    "Updates service properties. "
                    "Team write access is required for both old and new team."
                ),
                "operationId": "updateService",
                "parameters": [path_param("service_id", "Service id.")],
                "requestBody": json_body("Updated service properties.", SERVICE_SCHEMA),
                "responses": {
                    "200": response("Service updated.", SERVICE_SCHEMA),
                    "400": response("Validation error.", ERROR_SCHEMA),
                    "403": response("Access denied.", ERROR_SCHEMA),
                    "404": response("Service not found.", ERROR_SCHEMA),
                },
            },
            "delete": {
                "tags": ["services"],
                "summary": "Delete service",
                "description": (
                    "Soft-deletes a service. Existing alerts keep their service reference."
                ),
                "operationId": "deleteService",
                "parameters": [path_param("service_id", "Service id.")],
                "responses": {
                    "200": response("Service deleted.", DELETE_RESPONSE_SCHEMA),
                    "403": response("Access denied.", ERROR_SCHEMA),
                    "404": response("Service not found.", ERROR_SCHEMA),
                },
            },
        },
        "/api/services/match-rules": {
            "get": {
                "tags": ["services"],
                "summary": "List service match rules",
                "description": (
                    "Returns service match rules filtered by team_id, route_id or service_id. "
                    "At least one filter is required."
                ),
                "operationId": "listServiceMatchRules",
                "parameters": [
                    query_param(
                        "team_id",
                        "Filter by team id.",
                        {"type": "integer", "minimum": 1},
                    ),
                    query_param(
                        "route_id",
                        "Filter by route id.",
                        {"type": "integer", "minimum": 1},
                    ),
                    query_param(
                        "service_id",
                        "Filter by service id.",
                        {"type": "integer", "minimum": 1},
                    ),
                ],
                "responses": {
                    "200": response(
                        "List of service match rules.",
                        {"type": "array", "items": SERVICE_MATCH_RULE_SCHEMA},
                    ),
                    "400": response("Missing or invalid filter.", ERROR_SCHEMA),
                    "403": response("Access denied.", ERROR_SCHEMA),
                },
            },
        },
        "/api/services/{service_id}/match-rules": {
            "get": {
                "tags": ["services"],
                "summary": "List service match rules by service",
                "description": "Returns match rules attached to one service.",
                "operationId": "listMatchRulesByService",
                "parameters": [path_param("service_id", "Service id.")],
                "responses": {
                    "200": response(
                        "List of service match rules.",
                        {"type": "array", "items": SERVICE_MATCH_RULE_SCHEMA},
                    ),
                    "403": response("Access denied.", ERROR_SCHEMA),
                    "404": response("Service not found.", ERROR_SCHEMA),
                },
            },
            "post": {
                "tags": ["services"],
                "summary": "Create service match rule",
                "description": (
                    "Creates a rule that resolves incoming alerts to a service. "
                    "The service_id in URL and request body must match."
                ),
                "operationId": "createServiceMatchRule",
                "parameters": [path_param("service_id", "Service id.")],
                "requestBody": json_body(
                    "Service match rule properties.",
                    SERVICE_MATCH_RULE_SCHEMA,
                ),
                "responses": {
                    "201": response("Service match rule created.", SERVICE_MATCH_RULE_SCHEMA),
                    "400": response("Validation error.", ERROR_SCHEMA),
                    "403": response("Access denied.", ERROR_SCHEMA),
                    "404": response("Service not found.", ERROR_SCHEMA),
                },
            },
        },
        "/api/services/match-rules/{rule_id}": {
            "put": {
                "tags": ["services"],
                "summary": "Update service match rule",
                "description": "Updates one service match rule.",
                "operationId": "updateServiceMatchRule",
                "parameters": [path_param("rule_id", "Service match rule id.")],
                "requestBody": json_body(
                    "Updated service match rule properties.",
                    SERVICE_MATCH_RULE_SCHEMA,
                ),
                "responses": {
                    "200": response("Service match rule updated.", SERVICE_MATCH_RULE_SCHEMA),
                    "400": response("Validation error.", ERROR_SCHEMA),
                    "403": response("Access denied.", ERROR_SCHEMA),
                    "404": response("Service match rule not found.", ERROR_SCHEMA),
                },
            },
            "delete": {
                "tags": ["services"],
                "summary": "Delete service match rule",
                "description": "Soft-deletes one service match rule.",
                "operationId": "deleteServiceMatchRule",
                "parameters": [path_param("rule_id", "Service match rule id.")],
                "responses": {
                    "200": response("Service match rule deleted.", DELETE_RESPONSE_SCHEMA),
                    "403": response("Access denied.", ERROR_SCHEMA),
                    "404": response("Service match rule not found.", ERROR_SCHEMA),
                },
            },
        },
        "/api/services/{service_id}/links": {
            "get": {
                "tags": ["services"],
                "summary": "List service links",
                "description": "Returns dashboard, metrics, logs, repository or documentation links for one service.",
                "operationId": "listServiceLinks",
                "parameters": [path_param("service_id", "Service id.")],
                "responses": {
                    "200": response(
                        "List of service links.",
                        {"type": "array", "items": SERVICE_LINK_SCHEMA},
                    ),
                    "403": response("Access denied.", ERROR_SCHEMA),
                    "404": response("Service not found.", ERROR_SCHEMA),
                },
            },
            "post": {
                "tags": ["services"],
                "summary": "Create service link",
                "description": "Creates a link for one service.",
                "operationId": "createServiceLink",
                "parameters": [path_param("service_id", "Service id.")],
                "requestBody": json_body("Service link properties.", SERVICE_LINK_SCHEMA),
                "responses": {
                    "201": response("Service link created.", SERVICE_LINK_SCHEMA),
                    "400": response("Validation error.", ERROR_SCHEMA),
                    "403": response("Access denied.", ERROR_SCHEMA),
                    "404": response("Service not found.", ERROR_SCHEMA),
                },
            },
        },
        "/api/services/links": {
            "get": {
                "tags": ["services"],
                "summary": "List links for readable services",
                "description": (
                    "Returns links for all readable services in the current scope. "
                    "Use team_id or service_id to narrow the result."
                ),
                "operationId": "listAllServiceLinks",
                "parameters": [
                    query_param("team_id", "Filter by team id.", {"type": "integer", "minimum": 1}),
                    query_param("service_id", "Filter by service id.", {"type": "integer", "minimum": 1}),
                ],
                "responses": {
                    "200": response(
                        "List of service links.",
                        {"type": "array", "items": SERVICE_LINK_SCHEMA},
                    ),
                    "403": response("Access denied.", ERROR_SCHEMA),
                },
            },
        },
        "/api/services/links/{link_id}": {
            "put": {
                "tags": ["services"],
                "summary": "Update service link",
                "description": "Updates one service link.",
                "operationId": "updateServiceLink",
                "parameters": [path_param("link_id", "Service link id.")],
                "requestBody": json_body("Updated service link.", SERVICE_LINK_SCHEMA),
                "responses": {
                    "200": response("Service link updated.", SERVICE_LINK_SCHEMA),
                    "400": response("Validation error.", ERROR_SCHEMA),
                    "403": response("Access denied.", ERROR_SCHEMA),
                    "404": response("Service link not found.", ERROR_SCHEMA),
                },
            },
            "delete": {
                "tags": ["services"],
                "summary": "Delete service link",
                "description": "Soft-deletes one service link.",
                "operationId": "deleteServiceLink",
                "parameters": [path_param("link_id", "Service link id.")],
                "responses": {
                    "200": response("Service link deleted.", DELETE_RESPONSE_SCHEMA),
                    "403": response("Access denied.", ERROR_SCHEMA),
                    "404": response("Service link not found.", ERROR_SCHEMA),
                },
            },
        },
        "/api/services/{service_id}/runbooks": {
            "get": {
                "tags": ["services"],
                "summary": "List service runbooks",
                "description": "Returns runbooks for one service.",
                "operationId": "listServiceRunbooks",
                "parameters": [path_param("service_id", "Service id.")],
                "responses": {
                    "200": response(
                        "List of service runbooks.",
                        {"type": "array", "items": SERVICE_RUNBOOK_SCHEMA},
                    ),
                    "403": response("Access denied.", ERROR_SCHEMA),
                    "404": response("Service not found.", ERROR_SCHEMA),
                },
            },
            "post": {
                "tags": ["services"],
                "summary": "Create service runbook",
                "description": "Creates a runbook for one service.",
                "operationId": "createServiceRunbook",
                "parameters": [path_param("service_id", "Service id.")],
                "requestBody": json_body("Service runbook properties.", SERVICE_RUNBOOK_SCHEMA),
                "responses": {
                    "201": response("Service runbook created.", SERVICE_RUNBOOK_SCHEMA),
                    "400": response("Validation error.", ERROR_SCHEMA),
                    "403": response("Access denied.", ERROR_SCHEMA),
                    "404": response("Service not found.", ERROR_SCHEMA),
                },
            },
        },
        "/api/services/runbooks": {
            "get": {
                "tags": ["services"],
                "summary": "List runbooks for readable services",
                "description": (
                    "Returns runbooks for all readable services in the current scope. "
                    "Use team_id or service_id to narrow the result."
                ),
                "operationId": "listAllServiceRunbooks",
                "parameters": [
                    query_param("team_id", "Filter by team id.", {"type": "integer", "minimum": 1}),
                    query_param("service_id", "Filter by service id.", {"type": "integer", "minimum": 1}),
                ],
                "responses": {
                    "200": response(
                        "List of service runbooks.",
                        {"type": "array", "items": SERVICE_RUNBOOK_SCHEMA},
                    ),
                    "403": response("Access denied.", ERROR_SCHEMA),
                },
            },
        },
        "/api/services/runbooks/{runbook_id}": {
            "put": {
                "tags": ["services"],
                "summary": "Update service runbook",
                "description": "Updates one service runbook.",
                "operationId": "updateServiceRunbook",
                "parameters": [path_param("runbook_id", "Service runbook id.")],
                "requestBody": json_body("Updated service runbook.", SERVICE_RUNBOOK_SCHEMA),
                "responses": {
                    "200": response("Service runbook updated.", SERVICE_RUNBOOK_SCHEMA),
                    "400": response("Validation error.", ERROR_SCHEMA),
                    "403": response("Access denied.", ERROR_SCHEMA),
                    "404": response("Service runbook not found.", ERROR_SCHEMA),
                },
            },
            "delete": {
                "tags": ["services"],
                "summary": "Delete service runbook",
                "description": "Soft-deletes one service runbook.",
                "operationId": "deleteServiceRunbook",
                "parameters": [path_param("runbook_id", "Service runbook id.")],
                "responses": {
                    "200": response("Service runbook deleted.", DELETE_RESPONSE_SCHEMA),
                    "403": response("Access denied.", ERROR_SCHEMA),
                    "404": response("Service runbook not found.", ERROR_SCHEMA),
                },
            },
        },
        "/api/services/{service_id}/dependencies": {
            "get": {
                "tags": ["services"],
                "summary": "List service dependencies",
                "description": "Returns upstream dependencies for one service.",
                "operationId": "listServiceDependencies",
                "parameters": [path_param("service_id", "Service id.")],
                "responses": {
                    "200": response(
                        "List of service dependencies.",
                        {"type": "array", "items": SERVICE_DEPENDENCY_SCHEMA},
                    ),
                    "403": response("Access denied.", ERROR_SCHEMA),
                    "404": response("Service not found.", ERROR_SCHEMA),
                },
            },
            "post": {
                "tags": ["services"],
                "summary": "Create service dependency",
                "description": (
                    "Creates a dependency from this service to another service. "
                    "Cross-team dependencies are allowed when the user can edit the source "
                    "service and read the target service."
                ),
                "operationId": "createServiceDependency",
                "parameters": [path_param("service_id", "Service id.")],
                "requestBody": json_body(
                    "Service dependency properties.",
                    SERVICE_DEPENDENCY_SCHEMA,
                ),
                "responses": {
                    "201": response("Service dependency created.", SERVICE_DEPENDENCY_SCHEMA),
                    "400": response("Validation error.", ERROR_SCHEMA),
                    "403": response("Access denied.", ERROR_SCHEMA),
                    "404": response("Service not found.", ERROR_SCHEMA),
                },
            },
        },
        "/api/services/dependencies": {
            "get": {
                "tags": ["services"],
                "summary": "List dependencies for readable services",
                "description": (
                    "Returns dependencies for all readable services in the current scope. "
                    "Use team_id or service_id to narrow the result."
                ),
                "operationId": "listAllServiceDependencies",
                "parameters": [
                    query_param("team_id", "Filter by team id.", {"type": "integer", "minimum": 1}),
                    query_param("service_id", "Filter by service id.", {"type": "integer", "minimum": 1}),
                ],
                "responses": {
                    "200": response(
                        "List of service dependencies.",
                        {"type": "array", "items": SERVICE_DEPENDENCY_SCHEMA},
                    ),
                    "403": response("Access denied.", ERROR_SCHEMA),
                },
            },
        },
        "/api/services/dependencies/{dependency_id}": {
            "put": {
                "tags": ["services"],
                "summary": "Update service dependency",
                "description": "Updates one service dependency.",
                "operationId": "updateServiceDependency",
                "parameters": [path_param("dependency_id", "Service dependency id.")],
                "requestBody": json_body(
                    "Updated service dependency.",
                    SERVICE_DEPENDENCY_SCHEMA,
                ),
                "responses": {
                    "200": response("Service dependency updated.", SERVICE_DEPENDENCY_SCHEMA),
                    "400": response("Validation error.", ERROR_SCHEMA),
                    "403": response("Access denied.", ERROR_SCHEMA),
                    "404": response("Service dependency not found.", ERROR_SCHEMA),
                },
            },
            "delete": {
                "tags": ["services"],
                "summary": "Delete service dependency",
                "description": "Soft-deletes one service dependency.",
                "operationId": "deleteServiceDependency",
                "parameters": [path_param("dependency_id", "Service dependency id.")],
                "responses": {
                    "200": response("Service dependency deleted.", DELETE_RESPONSE_SCHEMA),
                    "403": response("Access denied.", ERROR_SCHEMA),
                    "404": response("Service dependency not found.", ERROR_SCHEMA),
                },
            },
        },
        "/api/services/analytics": {
            "get": {
                "tags": ["services"],
                "summary": "Service alert analytics",
                "description": (
                    "Returns alert counters grouped by affected service. "
                    "Defaults to the last 30 days; days is clamped to 1..365."
                ),
                "operationId": "getServiceAnalytics",
                "parameters": [
                    query_param("team_id", "Filter by team id.", {"type": "integer", "minimum": 1}),
                    query_param("service_id", "Filter by service id.", {"type": "integer", "minimum": 1}),
                    query_param("days", "Time range in days.", {"type": "integer", "minimum": 1, "maximum": 365, "default": 30}),
                ],
                "responses": {
                    "200": response(
                        "Service analytics.",
                        {"type": "array", "items": SERVICE_ANALYTICS_SCHEMA},
                    ),
                    "403": response("Access denied.", ERROR_SCHEMA),
                    "404": response("Service not found.", ERROR_SCHEMA),
                },
            },
        },
        "/api/services/impact": {
            "get": {
                "tags": ["services"],
                "summary": "Service impact status",
                "description": (
                    "Returns computed service impact based on manual service status, "
                    "open alerts and direct upstream dependencies."
                ),
                "operationId": "getServiceImpact",
                "parameters": [
                    query_param("team_id", "Filter by team id.", {"type": "integer", "minimum": 1}),
                    query_param("service_id", "Filter by service id.", {"type": "integer", "minimum": 1}),
                    query_param("days", "Alert lookback range in days.", {"type": "integer", "minimum": 1, "maximum": 365, "default": 30}),
                ],
                "responses": {
                    "200": response(
                        "Service impact rows.",
                        {"type": "array", "items": SERVICE_IMPACT_SCHEMA},
                    ),
                    "403": response("Access denied.", ERROR_SCHEMA),
                    "404": response("Service not found.", ERROR_SCHEMA),
                },
            },
        },
    }
