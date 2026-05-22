---
title: Alerts
description: Working with alerts in IncidentRelay
---

# Alerts

Open:

```text
Alerts
```

The Alerts page shows incoming alerts after they are normalized, routed and stored.

## What you can see

You can view:

- status;
- severity;
- assignee;
- team;
- route;
- rotation;
- source;
- labels and payload details;
- routing errors;
- notification events;
- ACK/Resolve state.

## Alert statuses

```text
firing
acknowledged
resolved
silenced
```

| Status | Meaning |
|---|---|
| `firing` | Active alert that still needs attention |
| `acknowledged` | Someone accepted responsibility for the alert |
| `resolved` | Alert is closed |
| `silenced` | New alert matched an active silence and notifications were suppressed |

## Acknowledge

Acknowledge marks the alert as seen and accepted. It stops normal repeated reminder flow for that alert.

Required permission:

```text
Team responder, Team manager, or global admin
```

## Resolve

Resolve marks the alert as closed.

Required permission:

```text
Team responder, Team manager, or global admin
```

Resolved events from Alertmanager, Zabbix or generic webhooks should use the same fingerprint, event ID or grouping data as the original firing event.

## Notifications

When a new firing alert is created:

1. IncidentRelay finds a matching route.
2. It checks silences.
3. It assigns the current on-call user from the route rotation.
4. It sends notifications to route channels allowed by severity filters.

If a channel says `notification sent`, IncidentRelay handed the message to the external provider without an exception. It does not guarantee final delivery in a mailbox, chat, phone or webhook receiver.

## Reminders

Reminders are controlled by the alert rotation.

```text
rotation.reminder_interval_seconds = 0     reminders disabled
rotation.reminder_interval_seconds >= 60   reminders enabled
```

## Routing errors

If no route matches, or the referenced team is missing/inactive, the alert can be stored with routing error information. Check alert details and logs for:

```text
routing_error
route_id
team_id
team_slug
```
