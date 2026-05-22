# Zabbix integration

Zabbix is an incoming alert source.

Endpoint:

```text
POST /api/integrations/zabbix
```

Authentication uses a route intake token:

```text
Authorization: Bearer ROUTE_TOKEN
```

## Route setup

Create a route with:

```text
Source: zabbix
```

Attach at least one notification channel and copy the route intake token into the Zabbix media type or webhook configuration.

## Payload example

```json
{
  "status": "firing",
  "event_id": "123456",
  "trigger_id": "98765",
  "title": "High CPU load on host1",
  "message": "CPU load is above 90%",
  "severity": "high",
  "team": "infra",
  "labels": {
    "host": "host1",
    "service": "cpu",
    "environment": "prod"
  }
}
```

## Required payload content

A Zabbix payload should contain enough data to identify and describe an alert. Empty JSON objects should be rejected by validation.

Useful fields:

```text
event_id
trigger_id
title
subject
message
fingerprint
```

## Normalized fields

| IncidentRelay field | Source |
|---|---|
| `source` | `zabbix` |
| `team_slug` | `team`, `labels.team`, or `labels.oncall_team` |
| `external_id` | `event_id` or `trigger_id` |
| `title` | `title`, then `subject`, then default title |
| `message` | `message` |
| `severity` | `severity` |
| `labels` | `labels` |
| `status` | `status`, default `firing` |
