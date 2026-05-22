---
title: First Login and Setup
description: Initial setup in the IncidentRelay web UI
---

# First Login and Setup

Open:

```text
/login
```

Log in with the global admin user created by `manage.py create-admin`.

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

A group is the access boundary for users and teams.

## Step 2. Create users

Open:

```text
Administration -> Users
```

Create users and fill contact fields that will be used by notification channels:

| Contact field | Used by |
|---|---|
| Email | Email channel |
| Phone | Voice call channel |
| Mattermost user ID | Mattermost action attribution |
| Telegram user ID | Telegram actions |

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
Role: editor
```

Group roles:

| Role | UI label | Purpose |
|---|---|---|
| `viewer` | Group Viewer | Read access inside the group boundary |
| `editor` | Group Editor | Can create group operational resources such as teams |
| `user_admin` | Group Admin | Can create and manage users only inside this group boundary |

Only a global admin can add an existing user to a group or assign `user_admin`.

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

Click `Members` next to the team and use `Add user to selected team`.

Example:

```text
User: ivan
Role: manager
```

Team roles:

| Role | UI label | Purpose |
|---|---|---|
| `viewer` | Team Viewer | Can view team resources and alerts |
| `responder` | Team Responder | Can acknowledge and resolve alerts |
| `manager` | Team Manager | Can manage team resources, channels, routes, rotations and silences |

A user must already belong to the team group before being added to the team.

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

Reminder interval rules:

```text
0       disables reminders for this rotation
>= 60   enables reminders with this interval
1..59   invalid
```

## Step 7. Add rotation members

In `Rotations`, add users in order:

```text
Position 0: ivan
Position 1: petr
Position 2: sergey
```

## Step 8. Create notification channels

Open:

```text
Channels
```

Select:

```text
Group: Production
Team: infra
```

Create at least one channel. For example, Mattermost Bot API mode:

```text
Type: mattermost
Mode: Bot API with buttons and message updates
Mattermost URL: https://mattermost.example.com
Bot token: <token>
Channel ID: <channel-id>
Callback secret: optional
```

Channels do not have alert intake tokens. They only define where notifications are sent.

For email channels, configure SMTP globally and make sure assigned users have profile email addresses.

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

Copy the route intake token after creating the route. If a route token is lost, open Routes and click `Regenerate token` next to the route.

## Step 10. Send a test alert

Use the matching incoming integration endpoint and the route intake token.

The route must match the incoming payload and the route must have at least one enabled channel attached.
