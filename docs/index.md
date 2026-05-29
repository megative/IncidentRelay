---
title: IncidentRelay Documentation
description: Documentation for IncidentRelay self-hosted on-call scheduling, alert routing and notification service
---

# IncidentRelay Documentation

IncidentRelay is a self-hosted on-call scheduling, alert routing and notification service. It keeps teams, rotations, routes, notification channels, acknowledgements, resolves, reminders and escalations inside your own infrastructure.

!!! warning "Beta status"
    IncidentRelay is currently in **beta**. APIs, UI behavior, database schema, configuration options and packaging details may still change.

## Alert flow

```text
Monitoring system
  -> Incoming integration endpoint
  -> Route intake token
  -> Route match
  -> Service
  -> Team and rotation
  -> Notification channels
  -> ACK / Resolve
```

## Installation paths

Choose one installation method:

| Method | Recommended for | Start here |
|---|---|---|
| Docker Compose | quick start, testing, simple self-hosted deployments | [Docker Installation](getting-started/docker.md) |
| RPM package | RHEL, Rocky Linux, AlmaLinux, CentOS Stream | [RPM Installation](getting-started/rpm-installation.md) |
| Manual systemd | source checkout, custom Python environment, classic Linux VM | [Manual systemd Installation](getting-started/systemd.md) |

All production installations should run two processes:

```text
incidentrelay             # HTTP API, UI, incoming webhooks
incidentrelay-scheduler   # reminders, escalations, periodic jobs
```

Do not run scheduler jobs inside every web worker.

## Configuration

IncidentRelay reads the config path from:

```text
INCEDENTRELAY_CONFIG_FILE
```

Example:

```bash
export INCEDENTRELAY_CONFIG_FILE=/etc/incidentrelay/incidentrelay.conf
```

The old `ONCALL_CONFIG_FILE` name should not be used.

Read more: [Configuration](getting-started/configuration.md).

## Core concepts

| Concept | Description |
|---|---|
| Group | Access boundary and group-level administration scope |
| User | Person who can log in, be on-call, receive notifications or use personal API tokens |
| Team | Operational unit inside a group |
| Rotation | On-call schedule for a team |
| Route | Alert routing rule with its own intake token |
| Channel | Outgoing notification target such as Mattermost, Telegram, email, webhook or voice call |
| Alert | IncidentRelay alert created from an incoming integration |
| Silence | Rule that suppresses notifications for matching new alerts |
| Override | Temporary replacement for a rotation member |

Read more:

- [Groups and RBAC](concepts/groups-and-rbac.md)
- [Teams, Rotations and Routes](concepts/teams-rotations-routes.md)
- [Route Intake Tokens](concepts/route-intake-tokens.md)
- [Channels](concepts/channels.md)
- [Reminders and Escalations](concepts/reminders-and-escalations.md)

## RBAC summary

IncidentRelay uses two permission layers:

| Layer | Purpose |
|---|---|
| Group role | Defines access boundary and group-level user administration |
| Team role | Defines what a user can do inside a specific team |

Current role names:

```text
Group roles: viewer, editor, user_admin
Team roles:  viewer, responder, manager
```

Important rules:

- A user must belong to a group before they can be added to a team in that group.
- Adding a user to a team does not add the user to the group automatically.
- `user_admin` can create users only inside the selected group boundary.
- `editor` can create teams in a group, but does not automatically manage all teams.
- `manager` is the write role for a specific team.
- `responder` can acknowledge and resolve alerts without changing team settings.

Read more: [Groups and RBAC](concepts/groups-and-rbac.md).

## Integrations

IncidentRelay has two integration layers.

### Incoming alert sources

| Source | Endpoint | Documentation |
|---|---|---|
| Alertmanager | `POST /api/integrations/alertmanager` | [Alertmanager](integrations/alertmanager.md) |
| Zabbix | `POST /api/integrations/zabbix` | [Zabbix](integrations/zabbix.md) |
| Generic webhook | `POST /api/integrations/webhook` | [Generic webhook](integrations/generic-webhook.md) |

Incoming integrations use route intake tokens.

### Notification channels

| Channel | Documentation |
|---|---|
| Common channel behavior | [Notification channels](integrations/channels.md) |
| Mattermost | [Mattermost](integrations/mattermost.md) |
| Telegram | [Telegram](integrations/telegram.md) |
| Email | [Email](integrations/email.md) |
| Slack, Discord, Microsoft Teams, custom webhook | [Webhook-based channels](integrations/webhook-channels.md) |
| Voice call | [Voice call](integrations/voice-call.md) |

Notification channels do not have intake tokens. Routes receive alerts, then send notifications to attached channels.

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

- [API Overview](api/index.md)
- [Profile and Personal API Tokens](usage/profile-and-tokens.md)
- [Voice Call OpenAPI Notes](api/voice-call-openapi.md)

## First setup flow

```text
1. Install IncidentRelay
2. Configure the service and public_base_url
3. Run migrations
4. Create the first global admin
5. Create a group
6. Create or add users to the group
7. Assign group roles: viewer, editor, user_admin
8. Create a team
9. Add group users to the team
10. Assign team roles: viewer, responder, manager
11. Create a rotation
12. Add rotation members
13. Create a service
14. Add service links and runbooks
15. Create notification channels
16. Create a route and attach channels
17. Select a default service or configure service match rules
18. Copy the route intake token
19. Configure Alertmanager, Zabbix or webhook sender
20. Send a test alert
21. Acknowledge or resolve the alert
```

Read more: [First Login and Setup](getting-started/first-login.md).

## Project links

- Repository: [https://github.com/roxy-wi/IncidentRelay](https://github.com/roxy-wi/IncidentRelay)
- Swagger UI: `/docs`
- OpenAPI JSON: `/api/openapi.json`
