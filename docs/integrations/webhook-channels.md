---
title: Webhook-based notification channels
description: Slack, Discord, Microsoft Teams, and generic outbound webhook channels
---

# Webhook-based notification channels

Several notification channels use an outbound webhook URL.

These are outgoing channels, not incoming alert integrations.

```text
Incoming integration -> Route -> Webhook-based notification channel -> External service
```

## Slack

Slack channel config:

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

## Discord

Discord channel config:

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

## Microsoft Teams

Microsoft Teams channel config:

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

## Generic outbound webhook

Generic webhook notification channel config:

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

Use outbound webhook channels for internal automation, custom incident systems, or notification fan-out.

## Do not confuse with incoming generic webhook

| Direction | Documentation | Endpoint/config |
|---|---|---|
| Incoming alert source | [Generic webhook integration](generic-webhook.md) | `POST /api/integrations/webhook` |
| Outgoing notification channel | This page | `config.webhook_url` |

The incoming generic webhook creates alerts. The outgoing webhook channel sends notifications after a route has matched an alert.
