---
title: Voice call notification channel
description: Voice call channel configuration and global voice provider settings
---

# Voice call notification channel

Voice call is an outgoing notification channel. It places calls through the globally configured voice provider.

A user who creates a voice call channel does not choose the provider and does not configure provider credentials. Provider settings belong to the service configuration file.

## Recipient model

Calls are sent to the assigned user's profile phone number.

```text
Route -> Rotation -> Current assignee -> assignee.phone -> Voice provider
```

Required user field:

```text
User profile -> phone
```

If the assigned user has no phone number, IncidentRelay cannot place the call and returns an error similar to:

```text
voice_call phone is missing: set phone on the assigned user
```

## Channel config

Minimal voice call channel config:

```json
{}
```

Voice calls are usually limited to high urgency alerts:

```json
{
  "notify_on_severities": ["critical"]
}
```

You can also allow multiple severities:

```json
{
  "notify_on_severities": ["critical", "high"]
}
```

Do not put phone numbers, provider names, API tokens, or provider-specific config into channel config.

## Global voice configuration

Example service config:

```ini
[voice]
provider = stub
providers_dir = /usr/local/lib/incidentrelay/voice_providers
callback_secret = change-me
text_template = IncidentRelay alert {alert_id}. {title}. Severity {severity}. {message}. Press 1 to acknowledge. Press 2 to resolve.
dtmf_actions = {"1": "acknowledge", "2": "resolve"}

[voice_provider]
api_url = https://voice.example.com/api
api_token = ${VOICE_API_TOKEN}
timeout = 10
```

The `[voice_provider]` section is provider-specific and is passed to the selected provider.

## DTMF actions

DTMF actions define what happens when a user presses a digit during the call.

```ini
dtmf_actions = {"1": "acknowledge", "2": "resolve"}
```

Meaning:

```text
1 -> acknowledge alert
2 -> resolve alert
```

## Voice text template

The global voice text template can use placeholders:

| Placeholder | Description |
|---|---|
| `{alert_id}` | IncidentRelay alert ID |
| `{event_type}` | Notification event type |
| `{title}` | Alert title |
| `{message}` | Alert message |
| `{severity}` | Alert severity |
| `{status}` | Alert status |
| `{team}` | Alert team |
| `{assignee}` | Current assignee |
| `{source}` | Alert source |

## Troubleshooting

### Voice calls are not placed

Check:

1. The voice call channel is enabled.
2. The voice call channel is attached to the matched route.
3. The alert severity is allowed by `notify_on_severities`.
4. The alert has an assignee.
5. The assigned user has `phone` configured.
6. The global `[voice]` provider is configured.
7. The provider credentials in `[voice_provider]` are valid.

### `voice_call channel requires provider`

That is old behavior. The provider should be configured globally, not in channel config.

### `phone` or `test_phone` does not work in channel config

Phone numbers are not read from channel config. Set the phone number on the assigned user profile.
