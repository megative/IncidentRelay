---
title: IncidentRelay Documentation
description: Documentation for IncidentRelay self-hosted on-call and alert routing service
---

# IncidentRelay Documentation

IncidentRelay is a self-hosted on-call incident routing and escalation service.

It provides team schedules, routing rules, notification channels, acknowledgements, resolve workflows, reminders, escalation logic, and API integrations for monitoring systems and internal SRE tools.

## Main sections

- [Getting started](getting-started/index.md)
- [Main concepts](concepts/index.md)
- [Integrations](integrations/index.md)
- [Usage](usage/index.md)
- [Custom voice providers](voice-providers/index.md)
- [API](api/index.md)
- [Administration](administration/index.md)

## Key features

- Access groups and group-scoped resources
- On-call teams and rotations
- Rotation overrides
- Alert routes with route-level intake tokens
- Alertmanager, Zabbix, and generic webhook intake
- Mattermost, Slack, Telegram, Discord, Teams, email, webhook, and voice call notifications
- Acknowledge and Resolve workflows
- Repeated reminders for unacknowledged alerts
- Escalation to the next on-call user
- On-call calendar view
- JWT authentication
- RBAC-style group roles
- Personal API tokens
- Swagger/OpenAPI documentation
- JSON audit, alert intake, and error logs
