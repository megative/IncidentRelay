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

## Service assignment

After a route matches the incoming alert, IncidentRelay can attach the alert to a service.

There are two ways:

1. Select a default service on the route.
2. Configure service match rules.

Use a default service when all alerts through the route belong to the same system.

Use service match rules when one route receives alerts for multiple systems.

Example service match rule for RabbitMQ:

```json
{
  "labels": {
    "job": "RabbitMQ",
    "rabbitmq": {
      "op": "regex",
      "value": "^rabbitmq-cloud$"
    }
  }
}
```

This can attach matching alerts to the `RabbitMQ Cloud` service.

## Payload example

```json
{
  "status": "firing",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "RabbitMQClusterPartition",
        "severity": "critical",
        "instance": "rabbit-1",
        "team": "infra",
        "job": "RabbitMQ",
        "rabbitmq": "rabbitmq-cloud"
      },
      "annotations": {
        "summary": "RabbitMQ cluster partition detected",
        "description": "Erlang distribution link is not healthy"
      },
      "fingerprint": "rabbitmq-cloud-partition-rabbit-1"
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

Use the same fingerprint and grouping data for resolved events.

That lets IncidentRelay update the existing alert instead of creating a new one.
