# Getting Started

Choose the installation method that matches your environment.

## Installation methods

| Method | Use when | Guide |
|---|---|---|
| Docker Compose | You want the quickest start or a container-based deployment | [Docker Installation](docker.md) |
| RPM package | You use RHEL, Rocky Linux, AlmaLinux or CentOS Stream | [RPM Installation](rpm-installation.md) |
| Manual systemd | You want to run from source code or manage the Python environment yourself | [Manual systemd Installation](systemd.md) |

All methods use the same application model:

```text
web service        -> HTTP API, UI, incoming integrations
scheduler service  -> reminders, escalations, periodic jobs
```

## Common next steps

After installation:

1. Review [Configuration](configuration.md).
2. Run database migrations if your installation method did not run them automatically.
3. Create the first global admin user.
4. Open the web interface and follow [First Login and Setup](first-login.md).
5. Configure at least one route and one notification channel.
6. Send a test alert.

## Important path and environment names

The config file is selected by:

```text
INCEDENTRELAY_CONFIG_FILE
```

Use the exact name above. The older `ONCALL_CONFIG_FILE` name should not be used.

Recommended paths for non-container installations:

```text
/etc/incidentrelay/incidentrelay.conf
/var/lib/incidentrelay
/var/log/incidentrelay
/usr/local/lib/incidentrelay/voice_providers
```
