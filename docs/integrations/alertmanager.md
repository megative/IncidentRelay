---
title: Alertmanager Integration
description: Send Alertmanager alerts to IncidentRelay
---

# Alertmanager Integration

Endpoint:

```text
POST /api/integrations/alertmanager
```

Required header:

```http
Authorization: Bearer ROUTE_INTAKE_TOKEN
```

## Create a route

Create a route:

```text
Name: infra-alertmanager
Source: alertmanager
Team: infra
Rotation: infra-primary
Channels: infra-mattermost
Matchers JSON: {"labels": {"team": "infra"}}
Group by JSON: ["alertname", "instance"]
```

Copy the route intake token after creating the route.

## Send firing alert

```bash
curl -X POST http://127.0.0.1:8080/api/integrations/alertmanager \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ALERTMANAGER_ROUTE_TOKEN' \
  -d '{
    "status": "firing",
    "alerts": [
      {
        "status": "firing",
        "labels": {
          "alertname": "DiskFull",
          "severity": "critical",
          "team": "infra",
          "instance": "host1"
        },
        "annotations": {
          "summary": "Disk is full",
          "description": "/var is 95% full"
        },
        "fingerprint": "disk-full-host1-var"
      }
    ]
  }'
```

Example response:

```json
[
  {
    "id": 1,
    "team_id": 1,
    "team_slug": "infra",
    "route_id": 1,
    "rotation_id": 1,
    "routing_error": null,
    "created": true,
    "status": "firing",
    "assignee": "ivan"
  }
]
```

If `route_id` is `null`, the alert did not match a route.

Check `routing_error` for details.

## Send resolved alert

Use the same `fingerprint` for `firing` and `resolved`.

```bash
curl -X POST http://127.0.0.1:8080/api/integrations/alertmanager \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ALERTMANAGER_ROUTE_TOKEN' \
  -d '{
    "status": "resolved",
    "alerts": [
      {
        "status": "resolved",
        "labels": {
          "alertname": "DiskFull",
          "severity": "critical",
          "team": "infra",
          "instance": "host1"
        },
        "annotations": {
          "summary": "Disk is full",
          "description": "/var is OK"
        },
        "fingerprint": "disk-full-host1-var"
      }
    ]
  }'
```

## Alertmanager receiver example

```yaml
receivers:
  - name: incidentrelay-infra
    webhook_configs:
      - url: "https://incidentrelay.example.com/api/integrations/alertmanager"
        send_resolved: true
        http_config:
          authorization:
            type: Bearer
            credentials: "ALERTMANAGER_ROUTE_TOKEN"

route:
  receiver: incidentrelay-infra
  group_by:
    - alertname
    - instance
  group_wait: 10s
  group_interval: 1m
  repeat_interval: 30m
```

If your Alertmanager version cannot set the `Authorization` header, add it with a reverse proxy.
