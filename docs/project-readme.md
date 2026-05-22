# IncidentRelay

IncidentRelay is a self-hosted on-call scheduling, alert routing and notification service.

It provides:

- groups and RBAC;
- teams and rotations;
- route-based alert intake tokens;
- Alertmanager, Zabbix and generic webhook intake;
- Mattermost, Telegram, email, webhook-based and voice call notification channels;
- ACK and Resolve workflows;
- reminders and escalation;
- silences and rotation overrides;
- calendar view;
- personal API tokens;
- Swagger/OpenAPI documentation.

## Installation

Choose one method:

| Method | Documentation |
|---|---|
| Docker Compose | [Docker Installation](getting-started/docker.md) |
| RPM package | [RPM Installation](getting-started/rpm-installation.md) |
| Manual systemd | [Manual systemd Installation](getting-started/systemd.md) |

## Runtime services

IncidentRelay should run as separate services:

```text
incidentrelay             # web API, UI, incoming webhooks
incidentrelay-scheduler   # reminders, escalations, periodic jobs
```

Telegram worker is optional and only needed when Telegram polling/actions are used.

## Configuration

IncidentRelay reads config path from:

```text
INCEDENTRELAY_CONFIG_FILE
```

Example:

```bash
export INCEDENTRELAY_CONFIG_FILE=/etc/incidentrelay/incidentrelay.conf
```

Do not use the old `ONCALL_CONFIG_FILE` name.

## Database migrations

```bash
python manage.py migrate
```

## Create first admin

```bash
python manage.py create-admin \
  --username admin \
  --password 'change-me-123' \
  --email admin@example.com
```

## Email notifications

Email channel does not store recipients or SMTP transport settings.

- SMTP is configured globally in the config file.
- Emails are sent to the assigned user's profile email address.
- Email channel can optionally override the HTML template.

## Reminder intervals

Reminder interval is configured on rotations:

```text
0       disables reminders
>= 60   enables reminders
1..59   invalid
```

## API

Swagger UI:

```text
/docs
```

OpenAPI JSON:

```text
/api/openapi.json
```

## License

MIT
