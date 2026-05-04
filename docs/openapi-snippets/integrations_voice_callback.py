"""OpenAPI snippets for voice provider callback endpoint.

Use these snippets inside app/api/openapi/endpoints/integrations.py.
"""

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


VOICE_CALLBACK_PATH = {
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
                {
                    "name": "channel_id",
                    "in": "path",
                    "required": True,
                    "description": "Voice call notification channel id.",
                    "schema": {
                        "type": "integer",
                    },
                },
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
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": VOICE_CALLBACK_BODY_SCHEMA,
                    }
                },
            },
            "responses": {
                "200": {
                    "description": "Callback processed or ignored.",
                    "content": {
                        "application/json": {
                            "schema": VOICE_CALLBACK_RESPONSE_SCHEMA,
                        }
                    },
                },
                "400": {
                    "description": "Invalid callback payload, provider parse error or channel is not voice_call.",
                },
                "403": {
                    "description": "Invalid voice callback secret.",
                },
                "404": {
                    "description": "Channel or notification not found.",
                },
            },
        }
    }
}
