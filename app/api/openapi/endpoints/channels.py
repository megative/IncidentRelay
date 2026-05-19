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


SEVERITY_FILTER_SCHEMA = {
    "type": "array",
    "description": (
        "Optional channel-level alert severity filter. "
        "If empty or omitted, the channel receives all severities. "
        "Values are normalized, for example crit -> critical, "
        "warn -> warning, information -> info."
    ),
    "items": {
        "type": "string",
        "enum": ["critical", "high", "medium", "warning", "low", "info"],
    },
    "example": ["critical", "high"],
}

CHANNEL_SCHEMA = {
    "type": "object",
    "required": ["name", "channel_type", "config"],
    "properties": {
        "team_id": {
            "type": "integer",
            "nullable": True,
            "description": "Owner team id.",
        },
        "name": {"type": "string", "example": "infra-telegram"},
        "channel_type": {
            "type": "string",
            "enum": [
                "telegram",
                "slack",
                "mattermost",
                "webhook",
                "discord",
                "teams",
                "email",
                "voice_call",
            ],
            "example": "telegram",
        },
        "config": {
            "type": "object",
            "description": (
                "Channel-specific configuration. "
                "All channel types support notify_on_severities as an optional "
                "channel-level severity filter. "
                "Telegram requires bot_token and chat_id. "
                "Slack/Webhook/Discord/Teams require webhook_url. "
                "Mattermost can use webhook_url, or mode=bot_api with api_url, "
                "bot_token and channel_id for buttons and post updates. "
                "Email sends to the assigned user profile email and supports html_template. "
                "Voice call channels require provider. "
                "provider_config is passed to the selected provider."
            ),
            "properties": {
                "notify_on_severities": SEVERITY_FILTER_SCHEMA,
            },
            "additionalProperties": True,
            "example": {
                "mode": "bot_api",
                "api_url": "https://mattermost.example.com",
                "bot_token": "...",
                "channel_id": "...",
                "notify_on_severities": ["critical", "high"],
            },
        },
        "enabled": {"type": "boolean", "default": True},
    },
}

CHANNEL_CONFLICT_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "error": {"type": "string", "example": "conflict"},
        "message": {
            "type": "string",
            "example": "Channel with this name already exists in this team",
        },
        "details": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "field": {"type": "string", "example": "name"},
                    "loc": {
                        "type": "array",
                        "items": {"type": "string"},
                        "example": ["name"],
                    },
                    "message": {
                        "type": "string",
                        "example": "Channel name must be unique within a team",
                    },
                    "type": {"type": "string", "example": "unique"},
                    "input": {"type": "string", "example": "cloud-mail"},
                },
            },
        },
    },
}

VOICE_CALL_CONFIG_SCHEMA = {
    "type": "object",
    "description": (
        "Voice call channel configuration. "
        "The provider field selects a built-in or custom voice provider module. "
        "provider_config is passed to the selected provider. "
        "The provider may support TTS, call status callbacks, DTMF callbacks or status polling."
    ),
    "properties": {
        "provider": {
            "type": "string",
            "description": (
                "Voice provider module name. "
                "Built-in providers are loaded from app.notifiers.voice.providers. "
                "Custom providers are loaded from the configured voice providers directory."
            ),
            "example": "example_http",
        },
        "notify_on_severities": SEVERITY_FILTER_SCHEMA,
        "callback_secret": {
            "type": "string",
            "nullable": True,
            "description": (
                "Optional per-channel callback secret. "
                "If omitted, the global voice.callback_secret setting is used."
            ),
            "example": "change-me-channel-secret",
        },
        "text_template": {
            "type": "string",
            "description": (
                "Template for the spoken call text. "
                "Supported placeholders: {alert_id}, {event_type}, {title}, {message}, "
                "{severity}, {status}, {team}, {assignee}, {source}."
            ),
            "example": (
                "IncidentRelay alert {alert_id}. {title}. "
                "Severity {severity}. {message}. "
                "Press 1 to acknowledge. Press 2 to resolve."
            ),
        },
        "dtmf_actions": {
            "type": "object",
            "description": (
                "Maps phone keypad digits to IncidentRelay actions. "
                "Used when the provider sends DTMF callbacks."
            ),
            "additionalProperties": {
                "type": "string",
                "enum": ["acknowledge", "resolve"],
            },
            "example": {
                "1": "acknowledge",
                "2": "resolve",
            },
        },
        "provider_config": {
            "type": "object",
            "description": (
                "Provider-specific configuration. "
                "Values like ${VOICE_API_TOKEN} are resolved from environment variables "
                "before being passed to the provider."
            ),
            "additionalProperties": True,
            "example": {
                "api_url": "https://voice.example.com/api",
                "api_token": "${VOICE_API_TOKEN}",
                "from": "+77000000000",
                "timeout": 10,
            },
        },
    },
    "required": ["provider"],
    "additionalProperties": True,
}

VOICE_PROVIDER_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "description": "Provider name returned by the Provider class.",
            "example": "example_http",
        },
        "module": {
            "type": "string",
            "description": "Provider module name used in channel config.",
            "example": "example_http",
        },
        "capabilities": {
            "type": "object",
            "description": "Voice provider feature flags.",
            "properties": {
                "tts": {
                    "type": "boolean",
                    "description": "Provider can receive text for speech synthesis.",
                    "example": True,
                },
                "status_callback": {
                    "type": "boolean",
                    "description": "Provider can send call status callbacks.",
                    "example": True,
                },
                "dtmf_callback": {
                    "type": "boolean",
                    "description": "Provider can send DTMF button press callbacks.",
                    "example": True,
                },
                "status_polling": {
                    "type": "boolean",
                    "description": "Provider can return call status through polling.",
                    "example": False,
                },
            },
        },
    },
}

CHANNEL_DELETE_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "deleted": {"type": "boolean", "example": True},
        "id": {"type": "integer", "example": 1},
        "name": {"type": "string", "example": "infra-telegram"},
    },
}


def tags():
    """Return OpenAPI tags."""
    return [
        {
            "name": "channels",
            "description": (
                "Notification channels. Channels are connected to alert routes and are used to send "
                "initial notifications, reminders, escalations and resolve messages."
            ),
        }
    ]


def paths():
    """Return OpenAPI paths for channel endpoints."""
    return {
        "/api/channels/types": {
            "get": {
                "tags": ["channels"],
                "summary": "List supported channel types",
                "description": "Returns channel plugins supported by the service.",
                "operationId": "listChannelTypes",
                "responses": {"200": response("Supported channel types.")},
            }
        },
        "/api/channels": {
            "get": {
                "tags": ["channels"],
                "summary": "List channels",
                "description": "Returns notification channels. Optional team_id filters channels by owner team.",
                "operationId": "listChannels",
                "parameters": [
                    query_param(
                        "team_id",
                        "Filter channels by team id.",
                        {"type": "integer", "minimum": 1},
                    )
                ],
                "responses": {
                    "200": response(
                        "List of channels.",
                        {"type": "array", "items": CHANNEL_SCHEMA},
                    )
                },
            },
            "post": {
                "tags": ["channels"],
                "summary": "Create channel",
                "description": (
                    "Creates a notification channel. The response contains intake_token once. Store it safely and use it "
                    "as Authorization: Bearer TOKEN for incoming alert endpoints."
                ),
                "operationId": "createChannel",
                "requestBody": json_body("Channel properties.", CHANNEL_SCHEMA),
                "responses": {
                    "201": response("Channel created. The full intake_token is returned only in this response."),
                    "400": response("Validation error."),
                    "409": response("Channel name already exists in this team.", CHANNEL_CONFLICT_RESPONSE_SCHEMA),
                },
            },
        },
        "/api/channels/{channel_id}": {
            "get": {
                "tags": ["channels"],
                "summary": "Get channel",
                "description": "Returns one channel by id, including config.",
                "operationId": "getChannel",
                "parameters": [path_param("channel_id", "Channel id.")],
                "responses": {"200": response("Channel details.", CHANNEL_SCHEMA)},
            },
            "put": {
                "tags": ["channels"],
                "summary": "Update channel",
                "description": "Updates channel name, type, enabled flag and config.",
                "operationId": "updateChannel",
                "parameters": [path_param("channel_id", "Channel id.")],
                "requestBody": json_body("Updated channel properties.", CHANNEL_SCHEMA),
                "responses": {
                    "200": response("Channel updated."),
                    "400": response("Validation error."),
                    "409": response("Channel name already exists in this team.", CHANNEL_CONFLICT_RESPONSE_SCHEMA),
                },
            },
            "delete": {
                "tags": ["channels"],
                "summary": "Delete channel",
                "description": (
                    "Soft-deletes a notification channel by setting deleted=true and enabled=false. "
                    "Deleted channels are hidden from active channel lists and detached from routes. "
                    "Historical alerts are preserved."
                ),
                "operationId": "deleteChannel",
                "parameters": [path_param("channel_id", "Channel id.")],
                "responses": {
                    "200": response("Channel deleted.", CHANNEL_DELETE_RESPONSE_SCHEMA),
                    "403": response("Access denied."),
                    "404": response("Channel not found."),
                },
            },
        },
        "/api/channels/{channel_id}/disable": {
            "post": {
                "tags": ["channels"],
                "summary": "Disable channel",
                "description": (
                    "Disables a notification channel by setting enabled=false. "
                    "The channel stays visible and can be enabled again."
                ),
                "operationId": "disableChannel",
                "parameters": [path_param("channel_id", "Channel id.")],
                "responses": {
                    "200": response("Channel disabled.", CHANNEL_SCHEMA),
                    "403": response("Access denied."),
                    "404": response("Channel not found."),
                },
            },
        },
        "/api/channels/{channel_id}/enable": {
            "post": {
                "tags": ["channels"],
                "summary": "Enable channel",
                "description": "Enables a previously disabled notification channel by setting enabled=true.",
                "operationId": "enableChannel",
                "parameters": [path_param("channel_id", "Channel id.")],
                "responses": {
                    "200": response("Channel enabled.", CHANNEL_SCHEMA),
                    "403": response("Access denied."),
                    "404": response("Channel not found."),
                },
            },
        },
        "/api/channels/{channel_id}/test": {
            "post": {
                "tags": ["channels"],
                "summary": "Send test notification",
                "description": (
                    "Sends a test message through the selected channel. Use this to verify Telegram bot tokens, "
                    "webhook URLs and SMTP settings before attaching the channel to alert routes."
                ),
                "operationId": "testChannel",
                "parameters": [path_param("channel_id", "Channel id.")],
                "responses": {
                    "200": response("Test notification sent."),
                    "400": response("Test failed. The response contains the transport error."),
                },
            }
        },
        "/api/channels/voice-providers": {
            "get": {
                "tags": ["channels"],
                "summary": "List voice call providers",
                "description": (
                    "Returns built-in and custom voice call providers available on this instance. "
                    "Custom providers are loaded from the configured voice providers directory. "
                    "The response includes provider capabilities such as TTS, status callbacks, "
                    "DTMF callbacks and status polling."
                ),
                "operationId": "listVoiceCallProviders",
                "responses": {
                    "200": response(
                        "Available voice call providers.",
                        {
                            "type": "array",
                            "items": VOICE_PROVIDER_SCHEMA,
                            "example": [
                                {
                                    "name": "stub",
                                    "module": "stub",
                                    "capabilities": {
                                        "tts": True,
                                        "status_callback": True,
                                        "dtmf_callback": True,
                                        "status_polling": False,
                                    },
                                }
                            ],
                        },
                    )
                },
            }
        },
    }
