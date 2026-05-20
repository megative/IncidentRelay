---
title: Zabbix incoming integration
description: Send Zabbix-style events to IncidentRelay
---

# Zabbix incoming integration

Zabbix is an incoming alert source. It sends events to IncidentRelay, where they are matched by a route and delivered to notification channels.

## Endpoint

```text
POST /api/integrations/zabbix
```

Required header:

```http
Authorization: Bearer ROUTE_INTAKE_TOKEN
```

## Route setup

Create a route with source `zabbix`.

Example:

```text
Name: infra-zabbix
Source: zabbix
Team: infra
Rotation: infra-primary
Channels: infra-mattermost, infra-email
Matchers JSON: {}
Group by JSON: ["host", "trigger"]
```

Copy the route intake token after creating the route.

## Firing event example

```bash
curl -X POST http://127.0.0.1:8080/api/integrations/zabbix \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ZABBIX_ROUTE_TOKEN' \
  -d '{
    "event_id": "100500",
    "status": "firing",
    "severity": "high",
    "host": "host1",
    "trigger": "Disk space is low",
    "message": "/var is 95% full",
    "labels": {
      "team": "infra",
      "host": "host1",
      "trigger": "DiskSpaceLow"
    }
  }'
```

## Resolved event example

Use the same `event_id` for `firing` and `resolved`.

```bash
curl -X POST http://127.0.0.1:8080/api/integrations/zabbix \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ZABBIX_ROUTE_TOKEN' \
  -d '{
    "event_id": "100500",
    "status": "resolved",
    "severity": "high",
    "host": "host1",
    "trigger": "Disk space is low",
    "message": "/var is OK",
    "labels": {
      "team": "infra",
      "host": "host1",
      "trigger": "DiskSpaceLow"
    }
  }'
```

## Notes

- Use a stable `event_id` for firing/resolved lifecycle.
- Keep labels consistent with route matchers and grouping.
- Notification channels are configured separately and attached to the route.
