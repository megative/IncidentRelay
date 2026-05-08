---
title: IncidentRelay Documentation
description: Documentation for IncidentRelay self-hosted on-call and alert routing service
---

# IncidentRelay Documentation

IncidentRelay is a self-hosted on-call incident routing and escalation service.

It provides team schedules, routing rules, notification channels, acknowledgements, resolve workflows, reminders, escalation logic, and API integrations for monitoring systems and internal SRE tools.

!!! warning "Beta status"
    IncidentRelay is currently in **beta**. APIs, UI behavior, database schema, configuration options, and deployment details may still change.

---

## What IncidentRelay helps with

IncidentRelay is designed for teams that want to keep alert routing and on-call workflows inside their own infrastructure.

Typical flow:

```text
Monitoring system
  -> Integration endpoint
  -> Route intake token
  -> Route
  -> Team
  -> Rotation
  -> Notification channels
  -> ACK / Resolve
```

---

## Main sections

- [Getting started](getting-started/index.md)
- [Main concepts](concepts/index.md)
- [Integrations](integrations/index.md)
- [Usage](usage/index.md)
- [Custom voice providers](voice-providers/index.md)
- [API](api/index.md)
- [Administration](administration/index.md)

---

## Quick start

Choose the installation method that matches your environment.

### Systemd installation

Use this option for a classic Linux VM or bare-metal installation.

IncidentRelay should run as two separate services:

```text
incidentrelay-web.service        # HTTP API, UI, webhooks
incidentrelay-scheduler.service  # reminders, escalations, periodic jobs
```

Start here:

[Systemd Installation](getting-started/systemd.md)

### Docker installation

Use this option for container-based self-hosted deployments.

The default Docker Compose setup uses SQLite and starts:

```text
incidentrelay-web
incidentrelay-scheduler
```

PostgreSQL can be enabled later through a Compose override.

Start here:

[Docker Installation](getting-started/docker.md)

---

## Configuration

IncidentRelay reads the configuration file path from:

```text
INCEDENTRELAY_CONFIG_FILE
```

Example:

```bash
export INCEDENTRELAY_CONFIG_FILE=/etc/incidentrelay/incidentrelay.conf
```

For systemd:

```ini
Environment=INCEDENTRELAY_CONFIG_FILE=/etc/incidentrelay/incidentrelay.conf
```

For Docker Compose:

```yaml
environment:
  INCEDENTRELAY_CONFIG_FILE: /etc/incidentrelay/incidentrelay.conf
```

!!! note
    The old `ONCALL_CONFIG_FILE` variable should not be used for IncidentRelay.

Read more:

[Configuration](getting-started/configuration.md)

---

## Key features

- Access groups and group-scoped resources
- On-call teams and rotations
- Rotation overrides
- Alert routes with route-level intake tokens
- Alertmanager, Zabbix, and generic webhook intake
- Mattermost, Slack, Telegram, Discord, Teams, email, webhook, and voice call notifications
- Acknowledge and Resolve workflows
- Repeated reminders for unacknowledged alerts
- Escalation to the next on-call user
- On-call calendar view
- JWT authentication
- RBAC-style group roles
- Personal API tokens
- Swagger/OpenAPI documentation
- JSON audit, alert intake, and error logs

---

## Core concepts

| Concept | Description |
|---|---|
| Group | Access and isolation boundary |
| User | Person who can log in, receive alerts, or be on-call |
| Team | Operational unit inside a group |
| Rotation | On-call schedule for a team |
| Route | Alert routing rule with its own intake token |
| Channel | Notification target such as Mattermost, Slack, email, webhook, or voice |
| Alert | IncidentRelay alert created from an incoming integration |
| Silence | Rule that suppresses matching alerts |
| Override | Temporary rotation replacement |

Read more:

- [Groups and RBAC](concepts/groups-and-rbac.md)
- [Teams, Rotations, and Routes](concepts/teams-rotations-routes.md)
- [Route Intake Tokens](concepts/route-intake-tokens.md)
- [Channels](concepts/channels.md)

---

## Integrations

### Incoming alert sources

| Source | Documentation |
|---|---|
| Alertmanager | [Alertmanager integration](integrations/alertmanager.md) |
| Zabbix | [Zabbix integration](integrations/zabbix.md) |
| Generic webhook | [Generic webhook integration](integrations/generic-webhook.md) |

### Notification channels

IncidentRelay can notify users through:

- Mattermost
- Slack
- Telegram
- Discord
- Microsoft Teams
- Email
- Outbound webhooks
- Custom voice providers

Mattermost Bot API mode supports interactive buttons for:

```text
Acknowledge
Resolve
```

Read more:

- [Mattermost integration](integrations/mattermost.md)
- [Custom Voice Providers](voice-providers/index.md)

---

## Custom voice providers

IncidentRelay supports pluggable voice-call providers for self-hosted installations.

A custom provider can implement:

- text-to-speech call creation
- provider call ID tracking
- call status callbacks
- DTMF button callbacks
- ACK / Resolve actions from phone keypad
- optional call status polling

Custom providers are Python modules stored in:

```text
/usr/local/lib/incidentrelay/voice_providers
```

Start here:

- [Custom Voice Providers](voice-providers/index.md)
- [Provider API](voice-providers/provider-api.md)
- [Configuration](voice-providers/configuration.md)
- [Callbacks and DTMF](voice-providers/callbacks.md)
- [Security](voice-providers/security.md)
- [Troubleshooting](voice-providers/troubleshooting.md)

---

## API and automation

Swagger UI:

```text
/docs
```

OpenAPI JSON:

```text
/api/openapi.json
```

Useful pages:

- [API](api/index.md)
- [Voice Call OpenAPI Notes](api/voice-call-openapi.md)
- [Profile and API Tokens](usage/profile-and-tokens.md)

---

## Operations

Operational documentation:

- [Scheduler](administration/scheduler.md)
- [Logging](administration/logging.md)
- [Demo Data](administration/demo-data.md)
- [Schema Check](administration/schema-check.md)
- [Troubleshooting](administration/troubleshooting.md)

The scheduler should run as a separate process or container:

```text
incidentrelay-web        # HTTP API, UI, webhooks
incidentrelay-scheduler  # reminders, escalations, periodic jobs
```

Do not run scheduler jobs inside every web worker.

---

## Common first setup flow

After installation and first login:

```text
1. Create a group
2. Create users
3. Add users to the group
4. Create a team
5. Add users to the team
6. Create a rotation
7. Add rotation members
8. Create notification channels
9. Create a route
10. Copy the route intake token
11. Configure Alertmanager, Zabbix, or webhook sender
12. Send a test alert
13. Acknowledge or resolve the alert
```

Read more:

[First Login and Initial Setup](getting-started/first-login.md)

---

## Recommended reading order

For a new installation:

```text
1. Systemd Installation or Docker Installation
2. Configuration
3. First Login
4. Groups and RBAC
5. Teams, Rotations, and Routes
6. Channels
7. Integrations
8. Scheduler
9. Troubleshooting
```

For custom voice integrations:

```text
1. Custom Voice Providers
2. Provider API
3. Configuration
4. Callbacks and DTMF
5. Security
6. Troubleshooting
```

---

## Project links

- Repository: [https://github.com/roxy-wi/IncidentRelay](https://github.com/roxy-wi/IncidentRelay)
- Swagger UI: `/docs`
- OpenAPI JSON: `/api/openapi.json`
