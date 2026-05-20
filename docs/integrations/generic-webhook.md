---
title: Generic webhook incoming integration
description: Send custom webhook alerts to IncidentRelay
---

# Generic webhook incoming integration

The generic webhook endpoint is an incoming alert source for internal tools or monitoring systems that do not use Alertmanager or Zabbix formats.

## Endpoint

```text
POST /api/integrations/webhook
```

Required header:

```http
Authorization: Bearer ROUTE_INTAKE_TOKEN
```

## Route setup

Create a route with source `webhook`.

Example:

```text
Name: infra-webhook
Source: webhook
Team: infra
Rotation: infra-primary
Channels: infra-mattermost, infra-email
Matchers JSON: {}
Group by JSON: ["alertname", "instance"]
```

Copy the route intake token after creating the route.

## Firing alert example

```bash
curl -X POST http://127.0.0.1:8080/api/integrations/webhook \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer WEBHOOK_ROUTE_TOKEN' \
  -d '{
    "title": "Disk is full",
    "message": "/var is 95% full",
    "severity": "critical",
    "status": "firing",
    "fingerprint": "disk-full-host1-var",
    "labels": {
      "team": "infra",
      "instance": "host1",
      "alertname": "DiskFull"
    }
  }'
```

## Resolved alert example

Use the same `fingerprint` for `firing` and `resolved`.

```bash
curl -X POST http://127.0.0.1:8080/api/integrations/webhook \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer WEBHOOK_ROUTE_TOKEN' \
  -d '{
    "title": "Disk is full",
    "message": "/var is OK",
    "severity": "critical",
    "status": "resolved",
    "fingerprint": "disk-full-host1-var",
    "labels": {
      "team": "infra",
      "instance": "host1",
      "alertname": "DiskFull"
    }
  }'
```

## Notes

- Use a stable `fingerprint` to deduplicate firing/resolved events.
- Use labels for route matchers and grouping.
- Outgoing webhook notification channels are documented separately: [Webhook-based channels](webhook-channels.md).
