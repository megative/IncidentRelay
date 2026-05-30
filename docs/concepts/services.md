title: Services
description: Logical services, affected systems, service routing and service impact analytics in IncidentRelay.

# Services

Services describe the logical system affected by an alert.

A service is not the same thing as a team or route:

- **Route** answers how the alert entered IncidentRelay.
- **Service** answers what system is affected.
- **Team** answers who owns the system.
- **Rotation / Escalation Policy** answers who should be notified.
- **Channel** answers where notifications are sent.

The service layer makes IncidentRelay service ownership while keeping routing simple and self-hosted.

## Alert flow

Without services:

```text
Monitoring system -> Route -> Team -> Rotation -> Notification channels -> ACK / Resolve
```

With services:

```text
Monitoring system -> Route -> Service -> Team -> Rotation / Escalation Policy -> Channels -> ACK / Resolve
```

A route can have a default service. Service match rules can override or refine that default based on alert labels, annotations or payload fields.

## Why services are useful

Services allow you to answer questions that are hard to answer with routes alone:

- Which system is broken?
- Which team owns that system?
- Which runbook should the on-call engineer open?
- Which dashboard, logs or traces are related to this service?
- Which upstream services may be causing this incident?
- Which services are noisy?
- Which services have the highest number of open critical alerts?

## Core service fields

A service has:

- `slug` — stable API/UI identifier, for example `rabbitmq-cloud`.
- `name` — human-readable name, for example `RabbitMQ Cloud`.
- `team_id` — owning team.
- `service_type` — `api`, `web`, `database`, `queue`, `cache`, `worker`, `cron`, `network`, `storage`, `infrastructure`, `external`, `other`.
- `environment` — `production`, `staging`, `development`, `testing`, `shared`.
- `criticality` — `low`, `medium`, `high`, `critical`.
- `tier` — `tier_1`, `tier_2`, `tier_3`, `tier_4`.
- `status` — `operational`, `degraded`, `partial_outage`, `major_outage`, `maintenance`, `disabled`, `unknown`.
- `labels`, `tags`, `metadata` — additional structured metadata.
- `default_rotation_id` — optional default rotation.
- `default_escalation_policy_id` — optional default escalation policy.

## Service match rules

Service match rules map incoming alerts to services.

A match rule belongs to a service and can optionally be scoped to a route.

Example:

```json
{
  "team_id": 1,
  "route_id": 10,
  "service_id": 5,
  "name": "RabbitMQ Cloud",
  "position": 10,
  "enabled": true,
  "matchers": {
    "labels": {
      "job": "RabbitMQ",
      "rabbitmq": {
        "op": "regex",
        "value": "^rabbitmq-cloud$"
      }
    }
  }
}
```

For an Alertmanager alert like this:

```json
{
  "status": "firing",
  "alerts": [
    {
      "labels": {
        "alertname": "RabbitMQClusterPartition",
        "severity": "critical",
        "job": "RabbitMQ",
        "rabbitmq": "rabbitmq-cloud"
      },
      "annotations": {
        "summary": "RabbitMQ Cluster Partition Detected"
      }
    }
  ]
}
```

the service match rule can attach the alert to `RabbitMQ Cloud`.

## Default route service

A route may have `service_id`.

Use this when all alerts coming through the route belong to the same service.

Example:

```text
Route: alertmanager-rabbitmq-prod
Default service: RabbitMQ Cloud
```

Use service match rules when one route receives alerts for many services.

Example:

```text
Route: alertmanager-prod
Service rule 1: labels.job = RabbitMQ -> RabbitMQ Cloud
Service rule 2: labels.job = PostgreSQL -> PostgreSQL Prod
Service rule 3: labels.app = billing-api -> Billing API
```

## Links

Service links point the on-call engineer to useful systems:

- dashboard
- metrics
- logs
- traces
- repository
- documentation
- status page
- wiki
- other

Example:

```json
{
  "link_type": "dashboard",
  "label": "RabbitMQ Grafana dashboard",
  "url": "https://grafana.example.com/d/rabbitmq-cloud",
  "priority": 10,
  "enabled": true
}
```

## Runbooks

Runbooks describe what to do when a service is broken.

Example:

```json
{
  "title": "RabbitMQ cluster partition",
  "url": "https://docs.example.com/runbooks/rabbitmq/cluster-partition",
  "severity": "critical",
  "priority": 10,
  "enabled": true,
  "matchers": {
    "labels": {
      "alertname": "RabbitMQClusterPartition"
    }
  }
}
```

Runbooks can be generic for a service or specific to an alert type.

## Dependencies

Dependencies describe upstream services.

Example:

```text
Billing API depends on PostgreSQL Prod
Frontend depends on Billing API
```

A dependency has:

- `depends_on_service_id`
- `dependency_type` — `hard`, `soft`, `external`, `informational`
- `criticality` — `required`, `important`, `optional`

Dependencies are used by service impact views to show whether a service may be affected by upstream incidents.

## Service impact

Service impact is computed from four values:

| Field | Meaning |
|---|---|
| `own_status` | Manual/current service status |
| `alert_impact_status` | Impact from open firing or acknowledged alerts |
| `dependency_impact_status` | Impact from upstream dependencies |
| `effective_status` | Worst status from own, alert and dependency impact |

Resolved and silenced alerts do not affect service impact.

Dependency impact respects dependency type and criticality:

| Dependency | Effect |
|---|---|
| `hard` + `required` | Can propagate major outage |
| `soft` / `important` | Reduces severe upstream impact |
| `optional` | Maximum downstream impact is degraded |
| `informational` | Visible in upstream issues, but does not change effective status |

Impact is calculated through upstream dependencies up to the configured impact depth.


### Dependency paths

When impact is propagated through multiple upstream dependencies, IncidentRelay shows the full dependency path.

Example:

```text
Frontend Web -> Billing API -> PostgreSQL Prod

root_cause_* points to the last affected service in the path.

path contains upstream services from the direct dependency to the root cause.

cycle_detected is true when a dependency cycle was found.

depth_limited is true when traversal stopped at the configured impact depth.
```

The API exposes this through:

```text
GET /api/services/impact
GET /api/services/impact?team_id=1
GET /api/services/impact?service_id=5
```

## Analytics

Service analytics group alerts by affected system.

Examples:

```text
GET /api/services/analytics?days=30
GET /api/services/analytics?team_id=1&days=7
GET /api/services/analytics?service_id=5&days=90
```

Useful metrics:

- total alerts
- open alerts
- firing alerts
- acknowledged alerts
- resolved alerts
- silenced alerts
- critical open alerts
- warning open alerts
- last alert time

## API examples

List services:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  https://incidentrelay.example.com/api/services
```

Create service:

```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  https://incidentrelay.example.com/api/services \
  -d '{
    "team_id": 1,
    "slug": "rabbitmq-cloud",
    "name": "RabbitMQ Cloud",
    "service_type": "queue",
    "environment": "production",
    "criticality": "critical",
    "tier": "tier_1",
    "status": "operational"
  }'
```

Create service match rule:

```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  https://incidentrelay.example.com/api/services/5/match-rules \
  -d '{
    "team_id": 1,
    "route_id": 10,
    "service_id": 5,
    "name": "RabbitMQ Cloud labels",
    "position": 10,
    "enabled": true,
    "matchers": {
      "labels": {
        "job": "RabbitMQ",
        "rabbitmq": {
          "op": "regex",
          "value": "^rabbitmq-cloud$"
        }
      }
    }
  }'
```

Create service link:

```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  https://incidentrelay.example.com/api/services/5/links \
  -d '{
    "link_type": "dashboard",
    "label": "Grafana",
    "url": "https://grafana.example.com/d/rabbitmq-cloud",
    "priority": 10,
    "enabled": true
  }'
```

Create runbook:

```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  https://incidentrelay.example.com/api/services/5/runbooks \
  -d '{
    "title": "RabbitMQ cluster partition",
    "url": "https://docs.example.com/runbooks/rabbitmq/cluster-partition",
    "severity": "critical",
    "priority": 10,
    "enabled": true
  }'
```

Create dependency:

```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  https://incidentrelay.example.com/api/services/5/dependencies \
  -d '{
    "depends_on_service_id": 2,
    "dependency_type": "hard",
    "criticality": "required",
    "enabled": true
  }'
```

## Recommended service naming

Use stable slugs:

```text
rabbitmq-cloud
postgresql-prod
billing-api
frontend-web
kubernetes-prod
```

Avoid environment-less ambiguous names like:

```text
api
database
queue
```

## Troubleshooting

### Service is not assigned to an alert

Check:

1. The route has a default `service_id`, or a service match rule exists.
2. The service match rule is enabled.
3. The service match rule is scoped to the correct route, or has no route scope.
4. The matcher fields match actual alert labels or annotations.
5. The service and owning team are enabled.

### Service is visible but cannot be edited

Service access follows team access. The user must have write access to the owning team or global admin permissions.

### Dependency cannot be created

Check that the source service is editable by the user and the target service is readable.
