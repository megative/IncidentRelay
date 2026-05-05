---
title: Configuration
description: IncidentRelay configuration
---

# Configuration

## Configuration file

IncidentRelay reads the config path from:

```text
INCEDENTRELAY_CONFIG_FILE
```

Example:

```bash
export INCEDENTRELAY_CONFIG_FILE=/etc/incedentrelay/incedentrelay.conf
```

For systemd:

```ini
Environment=INCEDENTRELAY_CONFIG_FILE=/etc/incedentrelay/incedentrelay.conf
```

For Docker Compose:

```yaml
environment:
  INCEDENTRELAY_CONFIG_FILE: /etc/incedentrelay/incedentrelay.conf
```

The old `ONCALL_CONFIG_FILE` name should not be used for IncidentRelay.

## Server section

```ini
[server]
host = 0.0.0.0
port = 8080
public_base_url = https://incidentrelay.example.com
```

`host` and `port` define where the service listens.

`public_base_url` is used for generated links and external callbacks. In production, set it to the real external URL.

## SQLite section

```ini
[database]
type = sqlite
path = /var/lib/incidentrelay/incidentrelay.db

[sqlite]
wal = true
busy_timeout = 5000
```

SQLite is the default database for small self-hosted installations.

## PostgreSQL section

```ini
[database]
type = postgresql
host = postgres
port = 5432
name = incidentrelay
user = incidentrelay
password = incidentrelay-change-me
```

Use PostgreSQL for larger installations, higher alert volume, or multiple web workers.

## Voice section

```ini
[voice]
provider = stub
providers_dir = /usr/local/lib/incidentrelay/voice_providers
callback_secret = change-me
```
