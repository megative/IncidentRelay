---
title: Teams, Rotations and Routes
description: How teams, rotations and routes work together
---

# Teams, Rotations and Routes

## Team

A team is an on-call team inside a group.

Example:

```text
Group: Production
Team: Infrastructure
Team slug: infra
```

The team slug is commonly used in Alertmanager labels:

```yaml
team: infra
```

## Rotation

A rotation defines who is on call and when the duty changes.

A rotation has:

- team;
- members;
- member order;
- handoff time;
- rotation type;
- reminder interval;
- optional overrides.

## Escalation

A team can define `Escalate after reminders`.

This value means how many reminder messages are sent before the alert is assigned to the next on-call user.

## Route

A route connects incoming alerts to a team, rotation, and notification channels.

Example:

```text
Source: alertmanager
Team: infra
Rotation: infra-primary
Channels: infra-mattermost, infra-voice-critical
Matchers: {"labels": {"team": "infra"}}
```

## Multiple routes for one team

One team can have multiple independent intake routes:

```text
infra-alertmanager -> source alertmanager -> Alertmanager token
infra-webhook      -> source webhook      -> Generic webhook token
infra-zabbix       -> source zabbix       -> Zabbix token
```

They can all point to the same team, rotation and notification channels.

This is useful when the same on-call team receives alerts from different systems.
