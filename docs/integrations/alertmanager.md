# Alertmanager integration

Alertmanager is an incoming alert source.

Endpoint:

```text
POST /api/integrations/alertmanager
```

Authentication uses a route intake token:

```text
Authorization: Bearer ROUTE_TOKEN
```

## Route setup

Create a route with:

```text
Source: alertmanager
```

Attach at least one notification channel and copy the route intake token into Alertmanager webhook configuration.

## Payload example

```json
{
  "status": "firing",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "DiskFull",
        "severity": "critical",
        "instance": "host1",
        "team": "infra"
      },
      "annotations": {
        "summary": "Disk is full",
        "description": "/var is 95% full"
      },
      "fingerprint": "disk-full-host1-var"
    }
  ]
}
```

## Normalized fields

| IncidentRelay field | Source |
|---|---|
| `source` | `alertmanager` |
| `team_slug` | `labels.team`, `labels.oncall_team`, or top-level `team` |
| `external_id` | `fingerprint` or `labels.alertname` |
| `title` | `annotations.summary`, then `labels.alertname` |
| `message` | `annotations.description` or `annotations.message` |
| `severity` | `labels.severity` |
| `labels` | alert item labels |
| `status` | item status or top-level status, default `firing` |

## Resolve events

Use the same fingerprint and grouping data for resolved events. That lets IncidentRelay update the existing alert instead of creating a new one.
