# Silences User Guide

## Table of Contents

- [Overview](#overview)
- [How a Silence Works](#how-a-silence-works)
- [When to Use Silences](#when-to-use-silences)
- [Silence Fields](#silence-fields)
- [Matcher Basics](#matcher-basics)
- [Supported Matcher Types](#supported-matcher-types)
  - [Exact Match](#exact-match)
  - [List Match](#list-match)
  - [Regular Expression Match](#regular-expression-match)
  - [Contains Match](#contains-match)
  - [Negative Match](#negative-match)
- [Common Matcher Fields](#common-matcher-fields)
  - [`source`](#source)
  - [`severity`](#severity)
  - [`title`](#title)
  - [`title_regex`](#title_regex)
  - [`labels`](#labels)
  - [`fields`](#fields)
- [Important Notes](#important-notes)
- [Alertmanager Silences](#alertmanager-silences)
  - [Alertmanager Normalized Fields](#alertmanager-normalized-fields)
  - [Alertmanager Payload Example](#alertmanager-payload-example)
  - [Silence by Alert Name and Instance](#silence-by-alert-name-and-instance)
  - [Silence by Severity](#silence-by-severity)
  - [Silence by Fingerprint](#silence-by-fingerprint)
  - [Silence by Annotation Text](#silence-by-annotation-text)
  - [Silence by Host Pattern](#silence-by-host-pattern)
- [Zabbix Silences](#zabbix-silences)
  - [Zabbix Normalized Fields](#zabbix-normalized-fields)
  - [Recommended Zabbix Payload Example](#recommended-zabbix-payload-example)
  - [Silence by Host](#silence-by-host)
  - [Silence by Host and Service](#silence-by-host-and-service)
  - [Silence by Event ID](#silence-by-event-id)
  - [Silence by Trigger ID](#silence-by-trigger-id)
  - [Silence by Message Text](#silence-by-message-text)
- [Generic Webhook Silences](#generic-webhook-silences)
  - [Generic Webhook Normalized Fields](#generic-webhook-normalized-fields)
  - [Recommended Webhook Payload Example](#recommended-webhook-payload-example)
  - [Silence by External ID](#silence-by-external-id)
  - [Silence by Service](#silence-by-service)
  - [Silence by Environment](#silence-by-environment)
  - [Silence by Custom Payload Field](#silence-by-custom-payload-field)
- [Match All Silences](#match-all-silences)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Overview

A silence temporarily suppresses notifications for matching alerts.

When an incoming alert matches an active silence:

- the alert is still saved in IncidentRelay;
- the alert status becomes `silenced`;
- notification messages are not sent to configured channels;
- an alert event is created to show that the alert matched a silence.

Silences do not delete alerts. They only prevent notifications for new matching `firing` alerts during the silence time window.

---

## How a Silence Works

The alert flow is:

```text
incoming integration payload
    ↓
normalization
    ↓
route detection
    ↓
team detection
    ↓
active silence lookup
    ↓
matcher comparison
    ↓
alert is created as firing or silenced
```

IncidentRelay does not match silences against the raw incoming JSON directly. First, every integration payload is converted into a normalized alert object.

A silence is checked only when the alert belongs to a team. Active silences are searched for that team only.

A silence is considered active when all of these conditions are true:

```text
silence.team == alert.team
silence.enabled == true
silence.deleted == false
silence.starts_at <= current_time
silence.ends_at > current_time
```

If multiple active silences match the same alert, the newest matching silence is used first.

---

## When to Use Silences

Use silences for temporary and expected alert noise, for example:

- planned maintenance;
- a known incident that is already being handled;
- a noisy host or service;
- temporary suppression of warning or info alerts;
- test alerts;
- suppressing alerts from one integration source;
- suppressing alerts for a specific environment, service, or host.

---

## Silence Fields

A silence usually contains these fields:

| Field | Description |
|---|---|
| `name` | Human-readable silence name |
| `team` | Team where the silence is active |
| `starts_at` | Start time |
| `ends_at` | End time |
| `reason` | Explanation for the silence |
| `matchers` | JSON object with alert matching rules |

Example:

```json
{
  "source": "alertmanager",
  "severity": "critical",
  "labels": {
    "alertname": "DiskFull",
    "instance": "host1"
  }
}
```

This silence matches Alertmanager alerts where:

```text
source == alertmanager
AND severity == critical
AND labels.alertname == DiskFull
AND labels.instance == host1
```

---

## Matcher Basics

All conditions inside one matcher object are combined with logical `AND`.

For example:

```json
{
  "source": "alertmanager",
  "severity": "critical",
  "labels": {
    "alertname": "DiskFull",
    "instance": "host1"
  }
}
```

means:

```text
source must be alertmanager
AND severity must be critical
AND labels.alertname must be DiskFull
AND labels.instance must be host1
```

If one condition does not match, the whole silence does not match.

---

## Supported Matcher Types

### Exact Match

Use exact match when the alert field must be equal to one value.

```json
{
  "severity": "critical"
}
```

The same can be used for labels:

```json
{
  "labels": {
    "instance": "host1"
  }
}
```

---

### List Match

Use a list when multiple values are acceptable.

```json
{
  "severity": ["warning", "critical"]
}
```

This matches alerts with either `warning` or `critical` severity.

You can also use lists inside labels:

```json
{
  "labels": {
    "environment": ["stage", "dev"]
  }
}
```

---

### Regular Expression Match

Use `regex` for pattern matching.

```json
{
  "labels": {
    "instance": {
      "regex": "^db-[0-9]+\.example\.com$"
    }
  }
}
```

This matches:

```text
db-1.example.com
db-25.example.com
```

It does not match:

```text
web-1.example.com
db-prod.example.com
```

---

### Contains Match

Use `contains` when only part of the value must match.

```json
{
  "fields": {
    "payload.annotations.description": {
      "contains": "/var"
    }
  }
}
```

This matches a value such as:

```text
/var is 95% full
```

---

### Negative Match

Use `not` when a field must not match a value.

```json
{
  "severity": {
    "not": "info"
  }
}
```

This matches all severities except `info`.

You can also combine `not` with a list:

```json
{
  "severity": {
    "not": ["info", "debug"]
  }
}
```

Or with a regular expression:

```json
{
  "labels": {
    "instance": {
      "not": {
        "regex": "^test-"
      }
    }
  }
}
```

---

## Common Matcher Fields

### `source`

Matches the integration source.

Supported normalized source values are:

```text
alertmanager
zabbix
webhook
```

Example:

```json
{
  "source": "alertmanager"
}
```

---

### `severity`

Matches normalized alert severity.

```json
{
  "severity": "critical"
}
```

Or:

```json
{
  "severity": ["warning", "critical"]
}
```

---

### `title`

Matches normalized alert title exactly.

```json
{
  "title": "Disk is full"
}
```

---

### `title_regex`

Matches normalized alert title using a regular expression.

```json
{
  "title_regex": "Disk.*full"
}
```

---

### `labels`

Matches values from normalized `labels`.

```json
{
  "labels": {
    "alertname": "DiskFull",
    "instance": "host1"
  }
}
```

Labels are usually the best option for stable matching because they are designed to identify alert metadata such as host, service, environment, team, or severity.

---

### `fields`

Matches any nested value from the normalized alert object using dot notation.

Example:

```json
{
  "fields": {
    "payload.fingerprint": "disk-full-host1-var"
  }
}
```

Another example:

```json
{
  "fields": {
    "payload.annotations.description": {
      "contains": "/var"
    }
  }
}
```

Dot notation means that:

```text
payload.annotations.description
```

reads:

```text
alert.payload.annotations.description
```

Use `fields` when you need to match values that are not present in top-level fields or labels.

---

## Important Notes

### Empty Matchers Match Everything

An empty matcher matches all alerts for the selected team:

```json
{}
```

Use this only when you intentionally want to silence all new `firing` alerts for the team during the selected time window.

### Silences Apply Only to New Incoming Alerts

A silence is checked when a new alert is created from an incoming payload.

If an alert already exists before the silence is created, that existing alert is not automatically changed to `silenced`.

### Silences Suppress Notifications, Not Alert Storage

A silenced alert is still stored in IncidentRelay. It can still be viewed in the alert list and used for statistics.

### Existing Alerts Are Updated Before New Silence Matching

If an incoming alert matches an existing alert by deduplication key and grouping window, IncidentRelay updates the existing alert instead of creating a new one. Silence matching is used when a new alert is created.

---

# Alertmanager Silences

Alertmanager sends payloads with an `alerts` list. IncidentRelay normalizes each item in that list as a separate alert.

## Alertmanager Normalized Fields

| Normalized field | Source in Alertmanager payload |
|---|---|
| `source` | Always `alertmanager` |
| `team_slug` | `labels.team`, `labels.oncall_team`, or top-level `payload.team` |
| `external_id` | `item.fingerprint` or `labels.alertname` |
| `dedup_key` | `item.fingerprint`, or generated from source, external ID, title, and labels |
| `title` | `annotations.summary`, then `labels.alertname`, then `Alertmanager alert` |
| `message` | `annotations.description` or `annotations.message` |
| `severity` | `labels.severity` |
| `labels` | `item.labels` |
| `payload` | Original Alertmanager alert item |
| `status` | `item.status` or top-level `payload.status`, default `firing` |

---

## Alertmanager Payload Example

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
        "team": "infra",
        "service": "node",
        "environment": "prod"
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

---

## Silence by Alert Name and Instance

```json
{
  "source": "alertmanager",
  "labels": {
    "alertname": "DiskFull",
    "instance": "host1"
  }
}
```

Use this to silence one Alertmanager alert type on one host.

---

## Silence by Severity

```json
{
  "source": "alertmanager",
  "severity": "warning"
}
```

Use this to silence all Alertmanager warning alerts for the selected team.

For multiple severities:

```json
{
  "source": "alertmanager",
  "severity": ["warning", "info"]
}
```

---

## Silence by Fingerprint

```json
{
  "source": "alertmanager",
  "fields": {
    "payload.fingerprint": "disk-full-host1-var"
  }
}
```

Use this when you want to silence one exact Alertmanager alert instance.

---

## Silence by Annotation Text

```json
{
  "source": "alertmanager",
  "fields": {
    "payload.annotations.description": {
      "contains": "/var"
    }
  }
}
```

Use this when the important match condition is inside Alertmanager annotations.

---

## Silence by Host Pattern

```json
{
  "source": "alertmanager",
  "labels": {
    "instance": {
      "regex": "^db-[0-9]+\.example\.com$"
    }
  }
}
```

Use this to silence alerts for a group of hosts.

---

# Zabbix Silences

Zabbix webhooks are normalized as single alerts.

## Zabbix Normalized Fields

| Normalized field | Source in Zabbix payload |
|---|---|
| `source` | Always `zabbix` |
| `team_slug` | `payload.team`, `labels.team`, or `labels.oncall_team` |
| `external_id` | `payload.event_id` or `payload.trigger_id` |
| `dedup_key` | `payload.fingerprint`, or generated from source, external ID, title, and labels |
| `title` | `payload.title`, then `payload.subject`, then `Zabbix alert` |
| `message` | `payload.message` |
| `severity` | `payload.severity` |
| `labels` | `payload.labels` |
| `payload` | Original Zabbix webhook payload |
| `status` | `payload.status`, default `firing` |

---

## Recommended Zabbix Payload Example

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

---

## Silence by Host

```json
{
  "source": "zabbix",
  "labels": {
    "host": "host1"
  }
}
```

---

## Silence by Host and Service

```json
{
  "source": "zabbix",
  "labels": {
    "host": "host1",
    "service": "cpu"
  }
}
```

---

## Silence by Event ID

```json
{
  "source": "zabbix",
  "fields": {
    "payload.event_id": "123456"
  }
}
```

Use this to silence one exact Zabbix event.

---

## Silence by Trigger ID

```json
{
  "source": "zabbix",
  "fields": {
    "payload.trigger_id": "98765"
  }
}
```

Use this to silence all alerts from a specific Zabbix trigger, depending on how your Zabbix webhook sends trigger IDs.

---

## Silence by Message Text

```json
{
  "source": "zabbix",
  "fields": {
    "payload.message": {
      "contains": "CPU load"
    }
  }
}
```

---

# Generic Webhook Silences

Generic webhook integration is useful when alerts come from a custom system.

## Generic Webhook Normalized Fields

| Normalized field | Source in webhook payload |
|---|---|
| `source` | Always `webhook` |
| `team_slug` | `payload.team`, `labels.team`, or `labels.oncall_team` |
| `external_id` | `payload.external_id` |
| `dedup_key` | `payload.fingerprint`, or generated from source, external ID, title, and labels |
| `title` | `payload.title`, default `Webhook alert` |
| `message` | `payload.message` |
| `severity` | `payload.severity` |
| `labels` | `payload.labels` |
| `payload` | Original webhook payload |
| `status` | `payload.status`, default `firing` |

---

## Recommended Webhook Payload Example

```json
{
  "status": "firing",
  "external_id": "deploy-incident-42",
  "fingerprint": "deploy-api-prod-42",
  "title": "API deploy failed",
  "message": "Deployment failed on api-prod-1",
  "severity": "critical",
  "team": "infra",
  "labels": {
    "service": "api",
    "environment": "prod",
    "host": "api-prod-1"
  },
  "details": {
    "deploy_id": "42",
    "region": "eu-1"
  }
}
```

---

## Silence by External ID

```json
{
  "source": "webhook",
  "fields": {
    "payload.external_id": "deploy-incident-42"
  }
}
```

---

## Silence by Service

```json
{
  "source": "webhook",
  "labels": {
    "service": "api"
  }
}
```

---

## Silence by Environment

```json
{
  "source": "webhook",
  "labels": {
    "environment": "stage"
  }
}
```

---

## Silence by Custom Payload Field

```json
{
  "source": "webhook",
  "fields": {
    "payload.details.region": "eu-1"
  }
}
```

Another example with `contains`:

```json
{
  "source": "webhook",
  "fields": {
    "payload.message": {
      "contains": "Deployment failed"
    }
  }
}
```

---

# Match All Silences

To silence all new `firing` alerts for the selected team, use an empty matcher:

```json
{}
```

This is useful for full-team maintenance windows.

Be careful: this suppresses notifications for every matching new alert in that team while the silence is active.

Recommended silence name examples:

```text
Maintenance window for all infra alerts
Full silence during datacenter migration
Suppress all alerts during test window
```

---

# Troubleshooting

## The silence does not work

Check the following:

1. The silence is enabled.
2. The silence is not deleted.
3. Current time is between `starts_at` and `ends_at`.
4. The alert belongs to the same team as the silence.
5. The matcher uses normalized fields, not only the raw incoming payload structure.
6. Label names match exactly.
7. Regex syntax is valid.
8. The alert is a new incoming `firing` alert.
9. The alert was not already created before the silence existed.
10. The route correctly resolves the incoming alert to the expected team.

## The silence matches too many alerts

Check for broad matchers such as:

```json
{}
```

or:

```json
{
  "source": "alertmanager"
}
```

or:

```json
{
  "severity": "warning"
}
```

Add more conditions, for example labels or payload fields:

```json
{
  "source": "alertmanager",
  "severity": "warning",
  "labels": {
    "service": "node",
    "environment": "prod"
  }
}
```

## Regex does not match

Remember to escape backslashes in JSON.

Correct:

```json
{
  "labels": {
    "instance": {
      "regex": "^db-[0-9]+\.example\.com$"
    }
  }
}
```

Incorrect:

```json
{
  "labels": {
    "instance": {
      "regex": "^db-[0-9]+\.example\.com$"
    }
  }
}
```

## Field matcher does not work

For `fields`, use the normalized alert object.

For original payload fields, start from `payload`.

Examples:

```json
{
  "fields": {
    "payload.event_id": "123456"
  }
}
```

```json
{
  "fields": {
    "payload.annotations.description": {
      "contains": "/var"
    }
  }
}
```

---

# Best Practices

1. Prefer labels for stable matching.

Good:

```json
{
  "source": "alertmanager",
  "labels": {
    "alertname": "DiskFull",
    "instance": "host1"
  }
}
```

2. Use `source` in most silences.

Good:

```json
{
  "source": "zabbix",
  "labels": {
    "host": "host1"
  }
}
```

This prevents accidental matching of alerts from another integration.

3. Use fingerprint or event ID for exact one-alert silences.

Alertmanager:

```json
{
  "source": "alertmanager",
  "fields": {
    "payload.fingerprint": "disk-full-host1-var"
  }
}
```

Zabbix:

```json
{
  "source": "zabbix",
  "fields": {
    "payload.event_id": "123456"
  }
}
```

4. Use short time windows.

Do not create long-running silences unless they are intentional.

5. Write a clear reason.

Good reasons:

```text
Planned maintenance on host1
Known disk issue, ticket INC-1234
Temporary suppression during migration
Test alert during webhook setup
```

6. Avoid empty matchers unless you really need to silence the whole team.

Empty matcher:

```json
{}
```

means:

```text
match all alerts for this team
```

7. Prefer exact labels over message text.

Message text can change. Labels are usually more stable.

Better:

```json
{
  "labels": {
    "service": "postgres"
  }
}
```

Less stable:

```json
{
  "fields": {
    "payload.message": {
      "contains": "postgres"
    }
  }
}
```
