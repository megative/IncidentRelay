---
title: Logging
description: IncidentRelay JSON logs and diagnostics
---

# Logging

Logs are configured here:

```ini
[logging]
log_file = ./logs/incedentrelay.log
json = true
requests = false
```

View logs:

```bash
tail -f ./logs/incedentrelay.log
```

## JSON error logs

Unhandled server errors return JSON with `error_id`:

```json
{
  "error": "Internal Server Error",
  "error_id": "uuid",
  "message": "Unexpected server error. Check JSON log by error_id."
}
```

Use the `error_id` to find the real traceback in the log file:

```bash
grep 'ERROR_ID_HERE' ./logs/incedentrelay.log
```

## Logging policy

The service writes only these JSON log records:

```text
user_action
alert_intake
error
```

Regular HTTP request logging is disabled by default:

```ini
[logging]
requests = false
```

User actions are logged through the audit layer.

Incoming alerts are logged when Alertmanager, Zabbix, or generic webhooks submit alerts.

Unhandled server errors are logged with `error_id`.

## Logging diagnostics

Request logging is hard-disabled in application code.

The service JSON log file accepts only these logger names:

```text
incedentrelay.audit
incedentrelay.alerts
incedentrelay.error
```

Check active logging settings:

```bash
curl -H 'Authorization: Bearer JWT_TOKEN' \
  http://127.0.0.1:8080/api/version/logging
```

Expected response:

```json
{
  "request_logging_registered": false,
  "allowed_loggers": [
    "incedentrelay.audit",
    "incedentrelay.alerts",
    "incedentrelay.error"
  ]
}
```
