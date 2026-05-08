---
title: Project README
description: Selling GitHub README for IncidentRelay
---

# Project README

This page mirrors the root `README.md`.

```markdown
# IncidentRelay

**Self-hosted on-call routing, alert delivery, and escalation for teams that want control over their incident workflow.**

IncidentRelay helps SRE, DevOps, platform, infrastructure, and operations teams route alerts to the right people through the right channels — without depending on a hosted incident-management platform.

It gives you the core building blocks of an on-call system:

- access groups and RBAC-style group roles;
- teams and on-call rotations;
- alert intake routes with per-route tokens;
- Alertmanager, Zabbix, and generic webhook integrations;
- Mattermost, Slack, Telegram, Discord, Microsoft Teams, email, webhook, and voice-call notifications;
- acknowledge and resolve workflows;
- reminders and escalation to the next on-call user;
- rotation overrides;
- calendar view for on-call schedules;
- personal API tokens;
- Swagger/OpenAPI documentation.

IncidentRelay is designed for **self-hosted environments** where teams need predictable behavior, clear ownership, easy integrations, and full control over alert routing.

---

## Why IncidentRelay?

Many teams need on-call routing, but do not always need a large SaaS incident platform.

IncidentRelay focuses on the practical workflow:

````text
Monitoring system -> Route -> Team -> Rotation -> Notification channels -> ACK / Resolve
````

A route owns its own intake token, so external systems send alerts to an exact alert path:

````text
ROUTE_INTAKE_TOKEN -> Route -> Team -> Rotation -> Channels
````

Channels only describe where notifications are delivered.  
Routes decide which team receives the alert and which channels are used.

This keeps alert delivery easier to reason about, easier to audit, and safer for self-hosted deployments.

---

## Highlights

### Self-hosted by design

Run IncidentRelay in your own environment, with your own database, your own network rules, and your own operational policies.

### Route-based alert intake

Alert intake tokens belong to routes, not channels. This makes it clear which incoming integration is allowed to submit alerts to which team and rotation.

### Multi-team and multi-group support

Use groups as access boundaries. Teams, rotations, routes, channels, alerts, and silences are scoped through groups and memberships.

### Escalation and reminders

Unacknowledged alerts can trigger repeated reminders and then escalate to the next on-call user according to the team configuration.

### Mattermost with real actions

Mattermost Bot API mode supports interactive `Acknowledge` and `Resolve` buttons, message updates, and severity-based attachment colors.

### Pluggable voice calls

IncidentRelay can be extended with custom voice providers for self-hosted installations. Providers can implement text-to-speech calls, call status callbacks, DTMF button callbacks, ACK / Resolve actions from phone keypad, and optional call status polling.

### API-first

IncidentRelay includes Swagger/OpenAPI documentation and personal API tokens with scopes for alerts, resources, and profile access.

---

## Supported integrations

### Incoming alert sources

| Source | Endpoint |
|---|---|
| Alertmanager | `POST /api/integrations/alertmanager` |
| Zabbix | `POST /api/integrations/zabbix` |
| Generic webhook | `POST /api/integrations/webhook` |

### Notification channels

| Channel | Notes |
|---|---|
| Mattermost | Incoming webhook mode or Bot API mode with buttons and updates |
| Slack | Webhook notifications |
| Telegram | Bot notifications |
| Discord | Webhook notifications |
| Microsoft Teams | Webhook notifications |
| Email | Email recipients |
| Webhook | Generic outbound webhook |
| Voice call | Pluggable provider API for self-hosted voice integrations |

---

## Quick start

Clone the repository:

````bash
git clone https://github.com/roxy-wi/IncidentRelay.git
cd IncidentRelay
````

Create a virtual environment:

````bash
python3 -m venv venv
source venv/bin/activate
````

Install dependencies:

````bash
pip install -r requirements.txt
````

Use the sample configuration for local development:

````bash
export ONCALL_CONFIG_FILE=$PWD/etc/incidentrelay/incidentrelay.conf
````

Run migrations:

````bash
python app/migrate.py migrate
````

Create the first administrator:

````bash
python manage.py create-admin \
  --username admin \
  --password 'change-me-123' \
  --email admin@example.com
````

Start the service:

````bash
python run.py
````

Open:

````text
http://127.0.0.1:8080/login
````

For production web serving, use Gunicorn or your preferred WSGI deployment model:

````bash
gunicorn -w 4 -b 0.0.0.0:8080 'app:create_app()'
````

Read the full installation guide:

[Installation](docs/getting-started/installation.md)

---

## Basic setup flow

After the first login:

````text
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
````

Detailed guide:

[First login and initial setup](docs/getting-started/first-login.md)

---

## Example Alertmanager request

````bash
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
````

More examples:

- [Alertmanager integration](docs/integrations/alertmanager.md)
- [Zabbix integration](docs/integrations/zabbix.md)
- [Generic webhook integration](docs/integrations/generic-webhook.md)

---

## Mattermost buttons and message updates

Mattermost has two modes.

**Incoming webhook mode** sends plain messages only.

**Bot API mode** is recommended when you want:

- `Acknowledge` button;
- `Resolve` button;
- message updates after ACK / Resolve;
- severity-based colors.

More details:

[Mattermost integration](docs/integrations/mattermost.md)

---

## Custom voice providers

IncidentRelay supports custom voice providers for self-hosted installations.

A provider is a Python module that can be placed into:

````text
/usr/local/lib/incidentrelay/voice_providers
````

Custom providers can implement:

- text-to-speech call creation;
- provider call ID tracking;
- call status callbacks;
- DTMF button callbacks;
- ACK / Resolve actions from phone keypad;
- optional call status polling.

Start here:

- [Custom Voice Providers](docs/voice-providers/index.md)
- [Provider API](docs/voice-providers/provider-api.md)
- [Configuration](docs/voice-providers/configuration.md)
- [Callbacks and DTMF](docs/voice-providers/callbacks.md)
- [Security](docs/voice-providers/security.md)
- [Troubleshooting](docs/voice-providers/troubleshooting.md)
- [Example providers](examples/voice_providers/)

---

## Documentation

| Topic | Link |
|---|---|
| Getting started | [docs/getting-started/](docs/getting-started/index.md) |
| Installation | [docs/getting-started/installation.md](docs/getting-started/installation.md) |
| Configuration | [docs/getting-started/configuration.md](docs/getting-started/configuration.md) |
| First login | [docs/getting-started/first-login.md](docs/getting-started/first-login.md) |
| Groups and RBAC | [docs/concepts/groups-and-rbac.md](docs/concepts/groups-and-rbac.md) |
| Teams, rotations, routes | [docs/concepts/teams-rotations-routes.md](docs/concepts/teams-rotations-routes.md) |
| Route intake tokens | [docs/concepts/route-intake-tokens.md](docs/concepts/route-intake-tokens.md) |
| Channels | [docs/concepts/channels.md](docs/concepts/channels.md) |
| Alertmanager | [docs/integrations/alertmanager.md](docs/integrations/alertmanager.md) |
| Zabbix | [docs/integrations/zabbix.md](docs/integrations/zabbix.md) |
| Generic webhook | [docs/integrations/generic-webhook.md](docs/integrations/generic-webhook.md) |
| Mattermost | [docs/integrations/mattermost.md](docs/integrations/mattermost.md) |
| Alerts | [docs/usage/alerts.md](docs/usage/alerts.md) |
| Calendar | [docs/usage/calendar.md](docs/usage/calendar.md) |
| Silences | [docs/usage/silences.md](docs/usage/silences.md) |
| Rotation overrides | [docs/usage/rotation-overrides.md](docs/usage/rotation-overrides.md) |
| Profile and API tokens | [docs/usage/profile-and-tokens.md](docs/usage/profile-and-tokens.md) |
| Logging | [docs/administration/logging.md](docs/administration/logging.md) |
| Troubleshooting | [docs/administration/troubleshooting.md](docs/administration/troubleshooting.md) |
| Custom voice providers | [docs/voice-providers/index.md](docs/voice-providers/index.md) |
| Swagger/OpenAPI notes | [docs/api/voice-call-openapi.md](docs/api/voice-call-openapi.md) |

Swagger UI is available at:

````text
/docs
````

OpenAPI JSON is available at:

````text
/api/openapi.json
````

---

## Documentation website

The documentation is ready to be published with MkDocs Material.

Install MkDocs Material:

````bash
pip install mkdocs-material
````

Run local preview:

````bash
mkdocs serve
````

Open:

````text
http://127.0.0.1:8000
````

---

## Demo data

Create demo data:

````bash
python manage.py demo-data
````

The command creates demo groups, users, teams, rotations, channels, routes, and route intake tokens.

Static demo-data check:

````bash
python app/check_demo_data.py
````

More details:

[Demo data](docs/administration/demo-data.md)

---

## Schema check

After running migrations, verify that all Peewee model tables and columns exist in the configured database:

````bash
python app/check_schema.py
````

Expected output:

````text
Schema check OK: all model tables and columns exist.
````

More details:

[Schema check](docs/administration/schema-check.md)

---

## Troubleshooting

If an alert is not visible or not delivered:

````text
1. Check that the correct route intake token was used.
2. Check that the endpoint matches the route source.
3. Check that route matchers match alert labels.
4. Check that the group is active.
5. Check that the team is active.
6. Check that the UI active group is correct.
7. Select "All my groups" and reload the Alerts page.
8. Check routing_error in the integration response.
9. Check JSON logs by error_id if the server returned one.
````

More details:

[Troubleshooting](docs/administration/troubleshooting.md)

---

## License

Add your project license here.
```
