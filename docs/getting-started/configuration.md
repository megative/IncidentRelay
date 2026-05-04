---
title: Configuration
description: Basic IncidentRelay configuration
---

# Configuration

The sample configuration file is here:

```text
etc/incedentrelay/incedentrelay.conf
```

For local development you can use it directly:

```bash
export ONCALL_CONFIG_FILE=$PWD/etc/incedentrelay/incedentrelay.conf
```

For a server installation, copy it to `/etc`:

```bash
sudo mkdir -p /etc/incedentrelay
sudo cp etc/incedentrelay/incedentrelay.conf /etc/incedentrelay/incedentrelay.conf
sudo editor /etc/incedentrelay/incedentrelay.conf
```

If `ONCALL_CONFIG_FILE` is not set, the service reads:

```text
/etc/incedentrelay/incedentrelay.conf
```

## Minimal SQLite configuration

```ini
[main]
secret_key = change-me
timezone = UTC
public_base_url = http://127.0.0.1:8080

[database]
type = sqlite
name = incedentrelay.db

[auth]
api_auth_required = true
rbac_enforced = true
jwt_secret = change-me-too
jwt_expire_minutes = 1440
jwt_cookie_name = incedentrelay_jwt
jwt_cookie_secure = false

[alerts]
reminder_after_seconds = 300
reminder_interval_seconds = 60
alert_group_window_seconds = 3600

[scheduler]
lock_ttl_seconds = 120

[logging]
log_file = ./logs/incedentrelay.log
log_level = INFO
json = true
requests = false

[mattermost]
action_secret = change-me

[voice]
provider = stub
providers_dir = /usr/local/lib/incidentrelay/voice_providers
callback_secret = change-me
```

## public_base_url

`public_base_url` is the public URL of IncidentRelay itself.

Example:

```ini
[main]
public_base_url = https://incidentrelay.example.com
```

Mattermost buttons and voice provider callbacks use this URL to call IncidentRelay back.

For Mattermost buttons:

```text
https://incidentrelay.example.com/api/integrations/mattermost/actions
```

For voice callbacks:

```text
https://incidentrelay.example.com/api/integrations/voice/callback/{channel_id}/{secret}
```

The Mattermost server URL in a Mattermost channel is different. It is the URL where IncidentRelay sends Mattermost API requests.

In short:

```text
public_base_url = where external services call IncidentRelay back
Mattermost URL = where IncidentRelay sends messages to Mattermost
```

For callbacks to work, `public_base_url` must be reachable from the external service.
