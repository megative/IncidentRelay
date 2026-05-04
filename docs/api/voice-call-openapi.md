---
title: Voice Call OpenAPI Notes
description: OpenAPI documentation notes for voice_call channels and callbacks
---

# Voice Call OpenAPI Notes

Swagger/OpenAPI should cover the HTTP API contract.

Developer documentation for writing provider modules should stay in:

```text
docs/voice-providers/
```

## Endpoints to document

```text
GET  /api/channels/voice-providers
POST /api/integrations/voice/callback/{channel_id}/{secret}
```

## Channel type

`channel_type` should include:

```text
voice_call
```

## Voice call channel config

Example:

```json
{
  "provider": "example_http",
  "call_on_severities": ["critical", "high"],
  "test_phone": "+77001234567",
  "callback_secret": "change-me-channel-secret",
  "text_template": "IncidentRelay alert {alert_id}. {title}. Severity {severity}. {message}. Press 1 to acknowledge. Press 2 to resolve.",
  "dtmf_actions": {
    "1": "acknowledge",
    "2": "resolve"
  },
  "provider_config": {
    "api_url": "https://voice.example.com/api",
    "api_token": "${VOICE_API_TOKEN}",
    "timeout": 10
  }
}
```

## Voice provider list response

Example:

```json
[
  {
    "name": "stub",
    "module": "stub",
    "capabilities": {
      "tts": true,
      "status_callback": true,
      "dtmf_callback": true,
      "status_polling": false
    }
  }
]
```

## Voice callback request

Example DTMF callback:

```json
{
  "call_id": "abc-123",
  "event_type": "dtmf",
  "status": "answered",
  "digit": "1"
}
```

Example status callback:

```json
{
  "call_id": "abc-123",
  "event_type": "status",
  "status": "completed"
}
```

## Voice callback response

Example:

```json
{
  "status": "processed",
  "events": [
    {
      "call_id": "abc-123",
      "event_type": "dtmf",
      "status": "answered",
      "digit": "1",
      "action": "acknowledge",
      "alert_id": 123
    }
  ]
}
```

## Snippets

Ready-to-copy OpenAPI snippets are included in:

```text
openapi-snippets/
```
