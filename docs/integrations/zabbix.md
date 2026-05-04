---
title: Zabbix Integration
description: Send Zabbix-style alerts to IncidentRelay
---

# Zabbix Integration

Endpoint:

```text
POST /api/integrations/zabbix
```

Required header:

```http
Authorization: Bearer ZABBIX_ROUTE_TOKEN
```

## Create a route

```text
Name: infra-zabbix
Source: zabbix
Team: infra
Rotation: infra-primary
Channels: infra-mattermost
Matchers JSON: {}
Group by JSON: ["host", "trigger"]
```

Copy the route intake token after creating the route.

## Send firing event

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

## Send resolved event

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
