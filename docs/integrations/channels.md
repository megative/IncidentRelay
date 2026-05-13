---
title: Channels
description: Notification channel types, severity filters, and voice call module configuration
---

# Channels

A channel is a notification destination.

IncidentRelay receives alerts through routes. A route then sends notifications to one or more channels.

Channels do not have alert intake tokens. Intake tokens belong to routes.

```text
Incoming alert -> Route -> Notification channels
```

Supported channel types:

```text
Mattermost
Slack
Telegram
Webhook
Discord
Teams
Email
Voice call
```

## Table of Contents

- [How Channels Work](#how-channels-work)
- [Channel Severity Filter](#channel-severity-filter)
- [Severity Normalization](#severity-normalization)
- [Telegram](#telegram)
- [Mattermost](#mattermost)
- [Slack](#slack)
- [Webhook](#webhook)
- [Discord](#discord)
- [Microsoft Teams](#microsoft-teams)
- [Email](#email)
- [Voice Call](#voice-call)
- [Voice Module Configuration](#voice-module-configuration)
- [Recommended Setup Examples](#recommended-setup-examples)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## How Channels Work

A route can have one or more notification channels.

When a new alert is created and should be notified, IncidentRelay checks every channel attached to the matched route.

For every channel, IncidentRelay checks:

```text
1. Is the channel enabled?
2. Does the channel severity filter allow this alert?
3. Can the notifier send or update this notification?
```

If the channel severity filter allows the alert, IncidentRelay sends the notification.

If the channel severity filter does not allow the alert, the channel is skipped.

---

## Channel Severity Filter

Every channel can limit which alert severities it receives.

Use the `notify_on_severities` field inside the channel `config`.

Example:

```json
{
  "notify_on_severities": ["critical", "high"]
}
```

This channel receives only `critical` and `high` alerts.

If `notify_on_severities` is empty or missing, the channel receives all alert severities.

Example without severity filter:

```json
{
  "bot_token": "123456:telegram-token",
  "chat_id": "-100123456789"
}
```

Example with severity filter:

```json
{
  "bot_token": "123456:telegram-token",
  "chat_id": "-100123456789",
  "notify_on_severities": ["critical", "high"]
}
```

The same `notify_on_severities` field is used for all channel types, including `voice_call`.

Do not use channel-specific severity fields such as:

```json
{
  "call_on_severities": ["critical"]
}
```

Use this instead:

```json
{
  "notify_on_severities": ["critical"]
}
```

---

## Severity Normalization

IncidentRelay normalizes common severity aliases before comparing them with `notify_on_severities`.

| Incoming value | Normalized value |
|---|---|
| `crit` | `critical` |
| `critical` | `critical` |
| `error` | `critical` |
| `fatal` | `critical` |
| `disaster` | `critical` |
| `high` | `high` |
| `avg` | `medium` |
| `average` | `medium` |
| `medium` | `medium` |
| `warn` | `warning` |
| `warning` | `warning` |
| `low` | `low` |
| `info` | `info` |
| `information` | `info` |
| `informational` | `info` |
| `not_classified` | `info` |
| `not classified` | `info` |

Recommended canonical severity values:

```text
critical
high
medium
warning
low
info
```

A channel configured with:

```json
{
  "notify_on_severities": ["critical"]
}
```

also receives alerts whose incoming severity is normalized to `critical`, for example `crit`, `error`, `fatal`, or `disaster`.

---

## Telegram

Telegram channels send alerts to a Telegram chat.

Example config:

```json
{
  "bot_token": "123456:telegram-token",
  "chat_id": "-100123456789"
}
```

Telegram channel with severity filter:

```json
{
  "bot_token": "123456:telegram-token",
  "chat_id": "-100123456789",
  "notify_on_severities": ["critical", "high"]
}
```

Use this when Telegram should receive only urgent alerts.

---

## Mattermost

Mattermost supports two modes:

```text
Incoming webhook mode
Bot API mode
```

Bot API mode is recommended when you need interactive buttons and message updates.

### Mattermost Incoming Webhook Mode

```json
{
  "mode": "webhook",
  "webhook_url": "https://mattermost.example.com/hooks/xxx"
}
```

With severity filter:

```json
{
  "mode": "webhook",
  "webhook_url": "https://mattermost.example.com/hooks/xxx",
  "notify_on_severities": ["critical", "high", "warning"]
}
```

### Mattermost Bot API Mode

```json
{
  "mode": "bot_api",
  "api_url": "https://mattermost.example.com",
  "bot_token": "mattermost-bot-token",
  "channel_id": "mattermost-channel-id",
  "callback_secret": "change-me"
}
```

With severity filter:

```json
{
  "mode": "bot_api",
  "api_url": "https://mattermost.example.com",
  "bot_token": "mattermost-bot-token",
  "channel_id": "mattermost-channel-id",
  "callback_secret": "change-me",
  "notify_on_severities": ["critical", "high", "warning"]
}
```

Recommended use:

```text
Mattermost main channel: critical, high, warning
Mattermost low-priority channel: low, info
```

---

## Slack

Slack channels usually use an incoming webhook URL.

```json
{
  "webhook_url": "https://hooks.slack.com/services/xxx/yyy/zzz"
}
```

With severity filter:

```json
{
  "webhook_url": "https://hooks.slack.com/services/xxx/yyy/zzz",
  "notify_on_severities": ["critical", "high"]
}
```

---

## Webhook

Webhook channels send alert notifications to a custom HTTP endpoint.

```json
{
  "webhook_url": "https://alerts.example.com/incidentrelay"
}
```

With severity filter:

```json
{
  "webhook_url": "https://alerts.example.com/incidentrelay",
  "notify_on_severities": ["critical", "high", "medium"]
}
```

Use webhook channels for integrations with internal tools, custom incident systems, or automation pipelines.

---

## Discord

Discord channels use a Discord webhook URL.

```json
{
  "webhook_url": "https://discord.com/api/webhooks/xxx/yyy"
}
```

With severity filter:

```json
{
  "webhook_url": "https://discord.com/api/webhooks/xxx/yyy",
  "notify_on_severities": ["critical", "high"]
}
```

---

## Microsoft Teams

Microsoft Teams channels use a Teams webhook URL.

```json
{
  "webhook_url": "https://outlook.office.com/webhook/xxx"
}
```

With severity filter:

```json
{
  "webhook_url": "https://outlook.office.com/webhook/xxx",
  "notify_on_severities": ["critical", "high", "warning"]
}
```

---

## Email

Email channels send alert notifications to one or more recipients.

```json
{
  "recipients": ["sre@example.com", "noc@example.com"]
}
```

With severity filter:

```json
{
  "recipients": ["sre@example.com", "noc@example.com"],
  "notify_on_severities": ["critical"]
}
```

Use this when email should be reserved for only the most important alerts.

Depending on your deployment, SMTP settings may be configured globally or inside the channel configuration.

Example with SMTP settings:

```json
{
  "recipients": ["sre@example.com"],
  "smtp_host": "smtp.example.com",
  "smtp_port": 587,
  "smtp_username": "incidentrelay@example.com",
  "smtp_password": "${SMTP_PASSWORD}",
  "from_email": "incidentrelay@example.com",
  "notify_on_severities": ["critical", "high"]
}
```

---

## Voice Call

Voice call channels place phone calls through a globally configured voice module.

A user who creates a voice call channel does not choose the voice provider and does not configure provider-specific settings.

The voice provider is configured by the system administrator in the IncidentRelay configuration file.

A voice call channel config should contain only user-level delivery policy, for example:

```json
{
  "notify_on_severities": ["critical"]
}
```

This channel places calls only for `critical` alerts.

If the config is empty, the voice call channel receives all alert severities:

```json
{}
```

### Where the phone number comes from

Phone numbers are not configured on the channel.

Real alert calls are sent to the phone number of the current alert assignee.

Required user setting:

```text
User -> phone
```

Expected flow:

```text
Route -> Rotation -> Current assignee -> assignee.phone -> Voice provider call
```

If the assigned user has no phone number, IncidentRelay cannot place the call.


---

## Voice Module Configuration

The voice provider and all provider-specific settings are configured in the IncidentRelay configuration file by the system administrator.

Example:

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

### `[voice]` section

| Setting | Description |
|---|---|
| `provider` | Name of the configured voice provider |
| `providers_dir` | Directory with custom voice provider modules |
| `callback_secret` | Secret used to verify callbacks from the voice provider |
| `text_template` | Text that the provider should say during the call |
| `dtmf_actions` | Digit-to-action mapping for phone keypad actions |

### `[voice_provider]` section

The `[voice_provider]` section contains provider-specific settings.

Examples:

```ini
api_url = https://voice.example.com/api
api_token = ${VOICE_API_TOKEN}
timeout = 10
```

These settings are passed to the selected voice provider.

Users who create channels should not see or edit these values.

### DTMF actions

DTMF actions define what happens when a user presses a digit during a call.

```ini
dtmf_actions = {"1": "acknowledge", "2": "resolve"}
```

This means:

```text
1 -> acknowledge alert
2 -> resolve alert
```

### Voice text template

The voice text template controls what the provider says during the call.

```ini
text_template = IncidentRelay alert {alert_id}. {title}. Severity {severity}. {message}. Press 1 to acknowledge. Press 2 to resolve.
```

Suggested placeholders:

| Placeholder | Description |
|---|---|
| `{alert_id}` | IncidentRelay alert ID |
| `{title}` | Alert title |
| `{message}` | Alert message |
| `{severity}` | Alert severity |
| `{status}` | Alert status |
| `{team}` | Alert team |
| `{assignee}` | Current assignee |
| `{source}` | Alert source |
| `{event_type}` | Notification event type |

---

## Recommended Setup Examples

### Example 1: Critical alerts to all urgent channels

Route channels:

| Channel | `notify_on_severities` |
|---|---|
| Mattermost main | `["critical", "high", "warning"]` |
| Telegram urgent | `["critical", "high"]` |
| Email | `["critical"]` |
| Voice call | `["critical"]` |

For a `warning` alert:

```text
Mattermost main: sent
Telegram urgent: skipped
Email: skipped
Voice call: skipped
```

For a `critical` alert:

```text
Mattermost main: sent
Telegram urgent: sent
Email: sent
Voice call: sent
```

### Example 2: Send all alerts to Mattermost but call only on critical

Mattermost:

```json
{
  "mode": "bot_api",
  "api_url": "https://mattermost.example.com",
  "bot_token": "mattermost-bot-token",
  "channel_id": "alerts-channel-id"
}
```

Voice call:

```json
{
  "notify_on_severities": ["critical"]
}
```

Mattermost receives all severities because it does not define `notify_on_severities`.

Voice call receives only `critical` alerts.

The voice provider itself is configured globally:

```ini
[voice]
provider = stub

[voice_provider]
api_url = https://voice.example.com/api
api_token = ${VOICE_API_TOKEN}
```

---

## Troubleshooting

### The channel does not receive alerts

Check the following:

1. The channel is enabled.
2. The channel is attached to the matched route.
3. The route matched the incoming alert.
4. The alert severity is included in `notify_on_severities`.
5. The channel configuration is valid.
6. The notifier provider has correct credentials.
7. The alert was not silenced.
8. The alert was not deduplicated into an existing alert that does not require a new notification.

Example:

```json
{
  "notify_on_severities": ["critical"]
}
```

This channel does not receive alerts with:

```text
warning
low
info
```

### The channel receives too many alerts

Check if `notify_on_severities` is missing or empty.

This config receives all severities:

```json
{
  "webhook_url": "https://alerts.example.com/hook"
}
```

This config receives only critical alerts:

```json
{
  "webhook_url": "https://alerts.example.com/hook",
  "notify_on_severities": ["critical"]
}
```

### Voice call does not work

Check the following:

1. The voice call channel is enabled.
2. The voice call channel is attached to the matched route.
3. The alert severity is allowed by `notify_on_severities`.
4. The alert has an assignee.
5. The assigned user has a phone number.
6. The global `[voice]` configuration has a valid provider.
7. The global `[voice_provider]` configuration has valid provider credentials.

Correct voice call channel config:

```json
{
  "notify_on_severities": ["critical"]
}
```

Correct user requirement:

```text
Assigned user has phone configured
```

Correct global voice module config:

```ini
[voice]
provider = stub
callback_secret = change-me

[voice_provider]
api_url = https://voice.example.com/api
api_token = ${VOICE_API_TOKEN}
```

### Voice call channel returns provider validation error

A voice call channel should not require `provider` in the channel config.

If you see an error like:

```text
voice_call channel requires provider
```

then the channel schema still contains old validation logic.

The provider must be configured globally in the IncidentRelay configuration file.

### Voice call is triggered for unexpected alerts

Check the voice call channel severity filter.

Correct:

```json
{
  "notify_on_severities": ["critical"]
}
```

Incorrect:

```json
{}
```

An empty config means that the voice call channel receives all severities.

### `call_on_severities` does not work

`call_on_severities` is not supported.

Use:

```json
{
  "notify_on_severities": ["critical"]
}
```

instead.

### `phone` or `test_phone` does not work in voice channel config

Phone numbers are not read from channel config.

Set the phone number on the assigned user profile instead.

---

## Best Practices

### Use route matchers for routing decisions

Use route matchers when different alerts must go to different routes, teams, rotations, or escalation policies.

Example:

```json
{
  "severity": "critical",
  "labels": {
    "service": "database"
  }
}
```

### Use channel filters for delivery decisions

Use `notify_on_severities` when the route is the same, but different channels should receive different alert severities.

| Channel | Purpose | `notify_on_severities` |
|---|---|---|
| Mattermost | Team visibility | `["critical", "high", "warning"]` |
| Telegram | Urgent mobile notifications | `["critical", "high"]` |
| Email | Important records | `["critical"]` |
| Voice call | Wake-up notifications | `["critical"]` |

### Keep voice calls strict

Voice calls should usually be limited to the highest severities.

Recommended:

```json
{
  "notify_on_severities": ["critical"]
}
```

Optional:

```json
{
  "notify_on_severities": ["critical", "high"]
}
```

Avoid:

```json
{
  "notify_on_severities": ["critical", "high", "warning", "low", "info"]
}
```

### Keep provider settings out of channel config

Provider settings should be configured globally by the system administrator.

Do not put this into channel config:

```json
{
  "provider": "stub",
  "provider_config": {
    "api_url": "https://voice.example.com/api",
    "api_token": "${VOICE_API_TOKEN}"
  }
}
```

Use the service configuration file instead:

```ini
[voice]
provider = stub

[voice_provider]
api_url = https://voice.example.com/api
api_token = ${VOICE_API_TOKEN}
```

### Prefer canonical severity names

Recommended:

```json
{
  "notify_on_severities": ["critical", "warning"]
}
```

Avoid:

```json
{
  "notify_on_severities": ["crit", "warn"]
}
```

Aliases work, but canonical names are easier to understand and maintain.

### Leave the filter empty only when intentional

This config receives all severities:

```json
{
  "notify_on_severities": []
}
```

This config also receives all severities:

```json
{}
```

Use this behavior only when the channel is intended to receive every alert from the route.
