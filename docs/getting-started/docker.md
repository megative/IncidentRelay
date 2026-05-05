---
title: Docker Installation
description: Run IncidentRelay with Docker Compose, SQLite by default, and optional PostgreSQL
---

# Docker Installation

The recommended self-hosted installation method is Docker Compose.

The default Compose setup uses SQLite and starts two containers:

```text
incidentrelay-web        # HTTP API, UI, webhooks
incidentrelay-scheduler  # reminders, escalations, periodic jobs
```

PostgreSQL is optional and can be enabled with a Compose override.

## Default architecture

```text
Docker Compose
├── incidentrelay-web
│   └── Gunicorn + Flask application
├── incidentrelay-scheduler
│   └── standalone APScheduler worker
└── incidentrelay-data
    └── SQLite database volume
```

SQLite database path inside the container:

```text
/var/lib/incidentrelay/incidentrelay.db
```

Default config path inside the container:

```text
/etc/incedentrelay/incedentrelay.conf
```

The config file is selected by:

```text
INCEDENTRELAY_CONFIG_FILE
```

## Quick start with SQLite

```bash
docker compose up -d --build
```

Open the UI:

```text
http://SERVER_IP:8080/login
```

Show logs:

```bash
docker compose logs -f incidentrelay-web
docker compose logs -f incidentrelay-scheduler
```

## Create the first admin user

```bash
docker compose exec incidentrelay-web \
  python manage.py create-admin \
    --username admin \
    --password 'change-me-123' \
    --email admin@example.com
```

## Default SQLite config

File:

```text
docker/incedentrelay.docker.conf
```

```ini
[main]
log_level = INFO
log_file = /var/log/incidentrelay/incidentrelay.log

[server]
host = 0.0.0.0
port = 8080
public_base_url = http://localhost:8080

[database]
type = sqlite
path = /var/lib/incidentrelay/incidentrelay.db

[sqlite]
wal = true
busy_timeout = 5000

[voice]
provider = stub
providers_dir = /usr/local/lib/incidentrelay/voice_providers
callback_secret = change-me
```

## Optional PostgreSQL

SQLite is the default database and is suitable for small self-hosted installations.

Use PostgreSQL for:

```text
- larger teams;
- high alert volume;
- multiple web workers;
- long-term production installations;
- future HA deployments.
```

Start with PostgreSQL:

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.postgres.yml \
  up -d
```

## External access

With this mapping:

```yaml
ports:
  - "8080:8080"
```

IncidentRelay is available externally on:

```text
http://SERVER_IP:8080
```

if the firewall allows port `8080`.

To expose IncidentRelay only on localhost and put Nginx or HAProxy in front of it:

```yaml
ports:
  - "127.0.0.1:8080:8080"
```

Production example:

```text
Internet -> Nginx/HAProxy :443 -> 127.0.0.1:8080 -> IncidentRelay
```

Set the public URL correctly:

```ini
[server]
public_base_url = https://incidentrelay.example.com
```

`public_base_url` is used for generated links and callbacks.

Do not leave it as `http://localhost:8080` in production.

## Custom voice providers

Custom voice providers can be mounted into:

```text
/usr/local/lib/incidentrelay/voice_providers
```

Compose mount:

```yaml
volumes:
  - ./custom_voice_providers:/usr/local/lib/incidentrelay/voice_providers:ro
```

After changing provider files, restart containers:

```bash
docker compose restart incidentrelay-web incidentrelay-scheduler
```
