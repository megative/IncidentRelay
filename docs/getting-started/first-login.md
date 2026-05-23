---
title: First Login and Setup
description: Initial setup in the IncidentRelay web UI
---

# First Login and Setup

Open:

```text
/login
```

Log in with the administrator user created by `manage.py create-admin`.

## Step 1. Create a group

Open:

```text
Administration -> Groups
```

Create a group:

```text
Slug: production
Name: Production
```

## Step 2. Create users

Open:

```text
Administration -> Users
```

Create users:

```text
ivan
petr
sergey
```

## Step 3. Add users to the group

Open:

```text
Administration -> Groups
```

Use `Add user to group`.

Example:

```text
Group: Production
User: ivan
Role: rw
```

Repeat for all users.

You can view group members on the same page by clicking `Members` next to the group.

## Step 4. Create a team

Open:

```text
Teams
```

Create a team:

```text
Group: Production
Slug: infra
Name: Infrastructure
Escalate after reminders: 2
```

`Escalate after reminders` means how many reminder messages are sent before the alert is assigned to the next on-call user.

## Step 5. Add users to the team

Open:

```text
Teams
```

Click `Members` next to the team.

Use `Add user to selected team`.

Example:

```text
User: ivan
Role: rw
```

Repeat for all users who should participate in the team schedule.

## Step 6. Create a rotation

Open:

```text
Rotations
```

Create a rotation:

```text
Team: infra
Name: infra-primary
Type: daily
Handoff time: 09:00
Timezone: UTC or your team timezone
Reminder interval: 300 seconds
```

A rotation is the calendar object used by routes and alerts.

When a rotation is created, IncidentRelay creates a `Default layer` inside it.

If `Add all active team members to this rotation` is enabled, all active team members are added to the default layer in team order.

## Step 7. Configure rotation layers

Open:

```text
Rotations -> Layers
```

A layer defines who rotates, when the handoff happens and when the layer is active.

For a simple 24/7 schedule, keep the default layer and add users:

```text
Position 0: ivan
Position 1: petr
Position 2: sergey
```

For business hours, nights and weekends, create separate layers:

```text
Layer: Business hours
Priority: 10
Active: Monday-Friday 09:00-18:00

Layer: Nights
Priority: 20
Active: Monday-Friday 18:00-09:00

Layer: Weekend
Priority: 30
Active: Saturday-Sunday 00:00-00:00
```

Higher priority active layers override lower priority active layers.

If a layer has no restrictions, it is active 24/7.

## Step 8. Verify the calendar

Open:

```text
Calendar
```

Check that the final schedule looks correct.

The calendar displays one rotation calendar at a time. If a team has multiple rotations, select the required rotation.

The calendar uses the final schedule:

```text
override > highest-priority active layer > no assignment
```

## Step 9. Create a notification channel

Open:

```text
Channels
```

Select:

```text
Group: Production
Team: infra
```

Create a channel, for example Mattermost Bot API mode:

```text
Type: mattermost
Mode: Bot API with buttons and message updates
Mattermost URL: https://mattermost.example.com
Bot token: <token>
Channel ID: <channel-id>
Callback secret: optional
```

Channels do not have alert intake tokens. They only define where notifications are sent.

## Step 10. Create a route

Open:

```text
Routes
```

Create a route:

```text
Team: infra
Source: alertmanager
Rotation: infra-primary
Channels: infra-mattermost
Matchers JSON: {"labels": {"team": "infra"}}
Group by JSON: ["alertname", "instance"]
```

Copy the route intake token after creating the route.

If a route token is lost, open Routes and click `Regenerate token` next to the route.

## Step 11. Send a test alert

Example Alertmanager request:

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

Open `Alerts` and verify that the alert was routed to the expected team and on-call user.
