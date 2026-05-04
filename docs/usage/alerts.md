---
title: Alerts
description: Working with alerts in IncidentRelay
---

# Alerts

Open:

```text
Alerts
```

You can:

- view status;
- view severity;
- view assignee;
- view route;
- view rotation;
- open details;
- acknowledge an alert;
- resolve an alert.

## Alert statuses

```text
firing
acknowledged
resolved
silenced
```

## Acknowledge

Acknowledging an alert marks it as seen and stops regular firing notifications for that alert flow.

## Resolve

Resolving an alert marks it as closed.

Resolved events from Alertmanager, Zabbix, or generic webhooks should use the same fingerprint/event id as the firing event.
