"""OpenAPI snippets for voice_call channels.

Use these snippets inside app/api/openapi/endpoints/channels.py.
"""

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
            "description": "Voice provider module name.",
            "example": "example_http",
        },
        "call_on_severities": {
            "type": "array",
            "description": "Alert severities that should trigger a real phone call.",
            "items": {
                "type": "string",
                "enum": ["critical", "high", "medium", "warning", "low", "info"],
            },
            "example": ["critical", "high"],
        },
        "phone": {
            "type": "string",
            "nullable": True,
            "description": (
                "Optional fallback phone number. "
                "For real alerts, the assigned user's phone is preferred."
            ),
            "example": "+77001234567",
        },
        "test_phone": {
            "type": "string",
            "nullable": True,
            "description": "Phone number used by the channel test endpoint.",
            "example": "+77001234567",
        },
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


VOICE_PROVIDERS_PATH = {
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
                "200": {
                    "description": "Available voice call providers.",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": VOICE_PROVIDER_SCHEMA,
                            }
                        }
                    },
                }
            },
        }
    }
}
