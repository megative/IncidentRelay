---
title: Generic Webhook Integration
description: Send generic webhook alerts to IncidentRelay
---

# Generic Webhook Integration

Endpoint:

```text
POST /api/integrations/webhook
```

Required header:

```http
Authorization: Bearer WEBHOOK_ROUTE_TOKEN
```

## Create a route

```text
Name: infra-webhook
Source: webhook
Team: infra
Rotation: infra-primary
Channels: infra-mattermost
Matchers JSON: {}
Group by JSON: ["alertname", "instance"]
```

Copy the route intake token after creating the route.

## Send firing alert

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

## Send resolved alert

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
