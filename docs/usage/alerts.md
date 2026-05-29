---
title: Alerts
description: Working with alerts in IncidentRelay
---

# Alerts

Open:

```text
Alerts
```

The Alerts page shows incoming alerts after they are normalized, routed, attached to a service when possible, and stored.

## What you can see

You can view:

- status;
- severity;
- assignee;
- team;
- service;
- route;
- rotation;
- source;
- labels and payload details;
- routing errors;
- notification events;
- ACK/Resolve state.

When displaying service or team names, IncidentRelay should use this order:

```text
name -> slug -> "-"
```

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

## Service context

If an alert is attached to a service, the alert view and notifications can show service context:

- service name;
- service links;
- matching runbooks;
- dependencies or impact information.

Service links are stable URLs for the whole service. Common examples:

- dashboard;
- metrics;
- logs;
- traces;
- repository;
- documentation;
- status page.

Runbooks can be generic or alert-specific:

```text
empty matchers -> show for all alerts of the service
matchers set   -> show only for matching alerts
```

Example generic runbook:

```json
{
  "title": "RabbitMQ troubleshooting",
  "url": "https://docs.example.com/runbooks/rabbitmq",
  "matchers": {}
}
```

Example alert-specific runbook:

```json
{
  "title": "RabbitMQ cluster partition",
  "url": "https://docs.example.com/runbooks/rabbitmq/cluster-partition",
  "severity": "critical",
  "matchers": {
    "labels": {
      "alertname": "RabbitMQClusterPartition"
    }
  }
}
```

## Acknowledge

Acknowledge marks the alert as seen and accepted.

It stops normal repeated reminder flow for that alert.

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
3. It attaches the alert to a default route service or to a service selected by service match rules.
4. It assigns the current on-call user from the route rotation, service default rotation, or escalation policy according to configured routing logic.
5. It sends notifications to route channels allowed by severity filters.

If a channel says `notification sent`, IncidentRelay handed the message to the external provider without an exception. It does not guarantee final delivery in a mailbox, chat, phone or webhook receiver.

Notifications may include service context:

```text
Service: RabbitMQ Cloud

Links:
- Grafana: https://grafana.example.com/d/rabbitmq-cloud
- Logs: https://logs.example.com/rabbitmq-cloud

Runbooks:
- RabbitMQ cluster partition (critical): https://docs.example.com/runbooks/rabbitmq/cluster-partition
```

## Reminders

Reminders are controlled by the alert rotation.

```text
rotation.reminder_interval_seconds = 0   reminders disabled
rotation.reminder_interval_seconds >= 60 reminders enabled
```

## Routing errors

If no route matches, or the referenced team is missing/inactive, the alert can be stored with routing error information.

Check alert details and logs for:

```text
routing_error
route_id
team_id
team_slug
```

## Alert has no service

If an alert is created but service is empty, check:

1. The route has a default service.
2. A service match rule exists.
3. The service match rule is enabled.
4. The service match rule is scoped to the correct route, or has no route scope.
5. The matcher fields match actual alert labels, annotations or payload fields.
6. The service and owning team are enabled.
