---
title: Getting Started
description: Install, configure and run IncidentRelay
---

# Getting Started

This section explains how to install IncidentRelay, configure it, initialize the database, create the first administrator, and complete the initial UI setup.

IncidentRelay can be installed in two main ways:

```text
Docker Compose     # recommended for container-based self-hosted deployments
systemd            # recommended for classic Linux VM or bare-metal deployments
```

Both installation methods use the same application model:

```text
incidentrelay-web        # HTTP API, UI, webhooks
incidentrelay-scheduler  # reminders, escalations, periodic jobs
```

The scheduler should run separately from the web process. Do not start scheduler jobs inside every web worker.

---

## Choose an installation method

### Docker Compose

Use Docker Compose if you want the simplest self-hosted deployment.

The default Docker setup uses SQLite and does not require an external database.

It starts:

```text
incidentrelay-web
incidentrelay-scheduler
```

Start here:

[Docker Installation](docker.md)

Default start command:

```bash
docker compose up -d --build
```

Use Docker when you want:

- a quick self-hosted installation;
- isolated runtime dependencies;
- simple upgrades;
- SQLite by default;
- optional PostgreSQL through Compose override.

---

### systemd

Use systemd if you want a classic Linux installation with a Python virtual environment.

It starts:

```text
incidentrelay-web.service
incidentrelay-scheduler.service
```

Start here:

[Systemd Installation](systemd.md)

Use systemd when you want:

- direct installation on a VM or bare-metal host;
- explicit service files;
- easier integration with existing Linux operations;
- manual control over Python environment and reverse proxy.

---

## Configuration file

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

[Configuration](configuration.md)

---

## Database choice

### SQLite

SQLite is the default database for quick and small self-hosted installations.

Recommended for:

```text
- testing
- small teams
- single-node installations
- one web process
- one scheduler process
```

Recommended SQLite settings:

```ini
[database]
type = sqlite
path = /var/lib/incidentrelay/incidentrelay.db

[sqlite]
wal = true
busy_timeout = 5000
```

For SQLite, keep web workers low, usually:

```text
--workers 1
```

### PostgreSQL

Use PostgreSQL for larger or long-running production installations.

Recommended for:

```text
- larger teams
- higher alert volume
- multiple web workers
- future HA deployments
- heavier API usage
```

Docker installation can enable PostgreSQL through a Compose override.

Systemd installation can use PostgreSQL by changing the `[database]` section in the config.

---

## Common setup flow

After installation, the initial setup is the same for Docker and systemd.

```text
1. Run database migrations
2. Create the first administrator
3. Log in to the web UI
4. Create a group
5. Create users
6. Add users to the group
7. Create a team
8. Add users to the team
9. Create a rotation
10. Add rotation members
11. Create notification channels
12. Create a route
13. Copy the route intake token
14. Configure Alertmanager, Zabbix, or a generic webhook sender
15. Send a test alert
16. Acknowledge or resolve the alert
```

Read more:

[First login and setup](first-login.md)

---

## Quick commands

### Docker

Start:

```bash
docker compose up -d --build
```

Run migrations manually if needed:

```bash
docker compose exec incidentrelay-web \
  python app/migrate.py migrate
```

Create the first administrator:

```bash
docker compose exec incidentrelay-web \
  python manage.py create-admin \
    --username admin \
    --password 'change-me-123' \
    --email admin@example.com
```

View logs:

```bash
docker compose logs -f incidentrelay-web
docker compose logs -f incidentrelay-scheduler
```

---

### systemd

Run migrations:

```bash
cd /var/www/incidentrelay
sudo -u www-data \
  INCEDENTRELAY_CONFIG_FILE=/etc/incidentrelay/incidentrelay.conf \
  /var/www/incidentrelay/venv/bin/python app/migrate.py migrate
```

Create the first administrator:

```bash
cd /var/www/incidentrelay
sudo -u www-data \
  INCEDENTRELAY_CONFIG_FILE=/etc/incidentrelay/incidentrelay.conf \
  /var/www/incidentrelay/venv/bin/python manage.py create-admin \
    --username admin \
    --password 'change-me-123' \
    --email admin@example.com
```

Start services:

```bash
sudo systemctl enable --now incidentrelay-web
sudo systemctl enable --now incidentrelay-scheduler
```

View logs:

```bash
journalctl -u incidentrelay-web -f
journalctl -u incidentrelay-scheduler -f
```

---

## Public URL

The application bind address and public URL are different things.

The web service should usually listen on:

```text
0.0.0.0:8080
```

or, behind a reverse proxy:

```text
127.0.0.1:8080
```

The public URL is configured separately:

```ini
[server]
public_base_url = https://incidentrelay.example.com
```

`public_base_url` is used for generated links and callback URLs.

For production, do not leave it as:

```text
http://localhost:8080
```

unless IncidentRelay is only used locally.

---

## Pages

- [Docker Installation](docker.md)
- [Systemd Installation](systemd.md)
- [Installation](installation.md)
- [Configuration](configuration.md)
- [First login and setup](first-login.md)
- [Quickstart checklist](quickstart.md)

---

## Recommended reading order

For a new installation:

```text
1. Docker Installation or Systemd Installation
2. Configuration
3. First login and setup
4. Quickstart checklist
```

Then continue with:

```text
1. Main concepts
2. Integrations
3. Usage
4. Administration
```
