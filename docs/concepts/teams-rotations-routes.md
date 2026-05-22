---
title: Teams, Rotations and Routes
description: How teams, rotations and routes work together
---

# Teams, Rotations and Routes

## Team

A team is an on-call unit inside a group.

Example:

```text
Group: Production
Team: Infrastructure
Team slug: infra
```

The team slug is commonly used in alert labels:

```yaml
team: infra
```

A team can have:

- members with team roles;
- rotations;
- routes;
- notification channels;
- silences;
- escalation policy.

## Rotation

A rotation defines who is on call and when duty changes.

A rotation has:

- team;
- members;
- member order;
- handoff time;
- rotation type;
- reminder interval;
- optional overrides.

Reminder interval rules:

```text
0       disables reminders for this rotation
>= 60   enables reminders with this interval in seconds
1..59   invalid
```

## Escalation

A team can define `Escalate after reminders`.

This value means how many reminder messages are sent before the alert is assigned to the next on-call user.

If reminders are disabled for a rotation by setting reminder interval to `0`, reminder-based escalation will not progress for alerts using that rotation.

## Route

A route connects incoming alerts to a team, rotation and notification channels.

Example:

```text
Source: alertmanager
Team: infra
Rotation: infra-primary
Channels: infra-mattermost, infra-voice-critical
Matchers: {"labels": {"team": "infra"}}
```

A route owns its own intake token. Channels do not have intake tokens.

## Multiple routes for one team

One team can have multiple independent intake routes:

```text
infra-alertmanager -> source alertmanager -> Alertmanager token
infra-webhook      -> source webhook      -> Generic webhook token
infra-zabbix       -> source zabbix       -> Zabbix token
```

They can all point to the same team, rotation and notification channels.
