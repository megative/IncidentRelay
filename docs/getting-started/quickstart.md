---
title: Quickstart Checklist
description: Typical IncidentRelay setup checklist
---

# Quickstart Checklist

```text
1. Log in as admin.
2. Create a group.
3. Create users.
4. Add users to the group.
5. Create a team.
6. Add users to the team.
7. Create a rotation.
8. Add rotation members.
9. Create a notification channel.
10. Create a route.
11. Copy the route intake token.
12. Configure Alertmanager, Zabbix, or a generic webhook.
13. Send a test alert.
14. Check the Alerts page.
15. Check notification delivery.
```

## Typical Alertmanager test

```bash
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
```
