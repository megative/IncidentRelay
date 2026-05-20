---
title: Mattermost notification channel
description: Mattermost webhook and Bot API notifications with ACK/Resolve buttons
---

# Mattermost notification channel

Mattermost is an outgoing notification channel. It does not receive alerts directly. Incoming alerts are received by an integration endpoint, matched to a route, and then delivered to the Mattermost channel attached to that route.

## Modes

Mattermost supports two modes.

| Mode | Supports buttons | Supports message updates | Recommended for |
|---|---:|---:|---|
| Incoming webhook | No | No | Simple notifications |
| Bot API | Yes | Yes | ACK/Resolve workflow |

Bot API mode is recommended when you need interactive actions.

## Incoming webhook mode

Config:

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

## Bot API mode

Config:

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

## ACK and Resolve actions

In Bot API mode, Mattermost messages can include:

```text
Acknowledge
Resolve
```

After ACK, the original post is updated and keeps only the Resolve button. After Resolve, the post is updated and buttons are removed.

## `public_base_url` vs Mattermost URL

`public_base_url` is the public URL of IncidentRelay. Mattermost calls this URL when a user clicks an action button.

Example action callback URL:

```text
https://incidentrelay.example.com/api/integrations/mattermost/actions
```

`api_url` is the Mattermost server URL. IncidentRelay uses it to send and update posts through the Mattermost Bot API.

```text
public_base_url = where Mattermost calls IncidentRelay back
api_url = where IncidentRelay sends messages to Mattermost
```

For buttons to work, `public_base_url` must be reachable from the Mattermost server.

## Recommended setup

```text
Main Mattermost channel: critical, high, warning
Low-priority Mattermost channel: low, info
Voice or email channel: critical only
```

## Troubleshooting

### Messages are sent, but buttons do not work

Check:

1. The channel uses Bot API mode.
2. `api_url`, `bot_token`, and `channel_id` are set.
3. `public_base_url` is configured and reachable from Mattermost.
4. The callback secret matches the expected value.
5. The user clicking the button has permission to ACK or Resolve the alert.

### Messages are skipped

Check `notify_on_severities` and the alert severity.
