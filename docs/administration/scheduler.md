---
title: Scheduler
description: Run IncidentRelay reminder and escalation scheduler separately from the web process
---

# Scheduler

IncidentRelay uses scheduler jobs for reminder, escalation and periodic maintenance logic.

The scheduler must run as a separate process and must not be started inside every web worker.

## Why separate scheduler process?

Do not run APScheduler inside multiple Gunicorn workers.

Bad model:

```text
gunicorn -w 4
├── worker 1 -> scheduler
├── worker 2 -> scheduler
├── worker 3 -> scheduler
└── worker 4 -> scheduler
```

This may duplicate reminders and escalations.

Recommended model:

```text
incidentrelay-web        # HTTP API, UI, webhooks
incidentrelay-scheduler  # one scheduler process
```

## Environment variables

The scheduler process should use:

```text
INCEDENTRELAY_CONFIG_FILE=/etc/incidentrelay/incidentrelay.conf
INCIDENTRELAY_SERVICE=scheduler
PYTHONUNBUFFERED=1
```

The web process should use:

```text
INCEDENTRELAY_CONFIG_FILE=/etc/incidentrelay/incidentrelay.conf
INCIDENTRELAY_SERVICE=web
PYTHONUNBUFFERED=1
```

## Standalone scheduler worker

File:

```text
app/scheduler_worker.py
```

```python
import logging
import signal
import time

from app import create_app

logger = logging.getLogger("oncall.scheduler")

_shutdown = False


def _handle_shutdown(signum, frame):
    """Handle container or systemd shutdown signals."""

    global _shutdown
    _shutdown = True

    logger.info(
        "scheduler shutdown requested",
        extra={"extra": {"signal": signum}},
    )

    try:
        from app.services.scheduler import stop_scheduler

        stop_scheduler()
    except Exception:
        logger.exception("failed to stop scheduler cleanly")


def main():
    """Start IncidentRelay scheduler as a standalone process."""

    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    app = create_app()

    with app.app_context():
        from app.services.scheduler import start_scheduler

        start_scheduler()

        logger.info("scheduler started")

        while not _shutdown:
            time.sleep(1)

    logger.info("scheduler stopped")


if __name__ == "__main__":
    main()
```

## Important application change

The scheduler should not autostart from `create_app()` in the web process.

If scheduler startup currently happens inside `create_app()`, guard it:

```python
import os

if os.getenv("INCIDENTRELAY_SERVICE") == "scheduler":
    start_scheduler()
```

If `app.scheduler_worker` starts the scheduler explicitly, it is usually better to remove automatic scheduler startup from `create_app()` completely.

Correct model:

```text
web process:
  create_app()
  no scheduler autostart

scheduler process:
  create_app()
  start_scheduler()
```

## systemd service

For classic installations without Docker, create:

```text
/etc/systemd/system/incidentrelay-scheduler.service
```

### Without virtualenv

```ini
[Unit]
Description=IncidentRelay Scheduler service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple

User=www-data
Group=www-data

WorkingDirectory=/var/www/incidentrelay

Environment=INCEDENTRELAY_CONFIG_FILE=/etc/incidentrelay/incidentrelay.conf
Environment=INCIDENTRELAY_SERVICE=scheduler
Environment=PYTHONUNBUFFERED=1

ExecStart=/usr/bin/python3 -m app.scheduler_worker

Restart=always
RestartSec=5

KillSignal=SIGTERM
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

### With virtualenv

```ini
[Unit]
Description=IncidentRelay Scheduler service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple

User=www-data
Group=www-data

WorkingDirectory=/var/www/incidentrelay

Environment=INCEDENTRELAY_CONFIG_FILE=/etc/incidentrelay/incidentrelay.conf
Environment=INCIDENTRELAY_SERVICE=scheduler
Environment=PYTHONUNBUFFERED=1

ExecStart=/var/www/incidentrelay/venv/bin/python -m app.scheduler_worker

Restart=always
RestartSec=5

KillSignal=SIGTERM
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

If your real config path is:

```text
/etc/incidentrelay/incidentrelay.conf
```

use:

```ini
Environment=INCEDENTRELAY_CONFIG_FILE=/etc/incidentrelay/incidentrelay.conf
```

The important part is to use the same path consistently across web and scheduler services.

## Web systemd service

The web service should explicitly identify itself as `web`:

```ini
Environment=INCIDENTRELAY_SERVICE=web
```

## Apply systemd changes

```bash
sudo systemctl daemon-reload
sudo systemctl enable incidentrelay-scheduler
sudo systemctl restart incidentrelay-scheduler
sudo systemctl status incidentrelay-scheduler
```

Logs:

```bash
journalctl -u incidentrelay-scheduler -f
```

## Troubleshooting

### Reminders are duplicated

Check that scheduler is not running inside web workers.

There should be one scheduler process.

### Scheduler cannot read config

Check `INCEDENTRELAY_CONFIG_FILE`:

```bash
systemctl show incidentrelay-scheduler --property=Environment
```

Check file permissions:

```bash
sudo -u www-data test -r /etc/incidentrelay/incidentrelay.conf
```

### SQLite database is locked

SQLite is suitable for small installations, but it has one writer lock.

Recommended SQLite config:

```ini
[sqlite]
wal = true
busy_timeout = 5000
```

For higher alert volume or multiple web workers, use PostgreSQL.
