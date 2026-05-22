---
title: Calendar
description: On-call calendar view
---

# Calendar

Open:

```text
Calendar
```

The calendar shows on-call duty calculated from rotations, rotation members and overrides.

## Views

The first calendar view should help users understand the current schedule across visible teams.

Typical usage:

- see all available teams for the current week;
- open one team schedule;
- switch to month view for a specific team;
- verify rotation handoff times;
- verify overrides.

## What the calendar uses

The calendar takes into account:

- rotation members;
- member order;
- rotation type;
- rotation interval and duration;
- handoff time;
- timezone;
- overrides.

## Troubleshooting

If the calendar looks wrong, check:

1. The rotation is enabled.
2. The rotation has members.
3. Member positions are correct.
4. Handoff time and timezone are correct.
5. Overrides do not replace the expected user.
6. The user has access to the team through group and team membership.
