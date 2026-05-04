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

The team members table shows the current team composition.

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
Reminder interval: 300 seconds
```

## Step 7. Add rotation members

In `Rotations`, add users in order:

```text
Position 0: ivan
Position 1: petr
Position 2: sergey
```

## Step 8. Create a notification channel

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
Bot token: <bot-token>
Channel ID: <mattermost-channel-id>
Callback secret: optional
```

Channels do not have alert intake tokens. They only define where notifications are sent.

## Step 9. Create a route

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
