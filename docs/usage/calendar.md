---
title: Calendar
description: On-call calendar view and final schedule rendering
---

# Calendar

Open:

```text
Calendar
```

The calendar shows the final on-call schedule for rotations.

A rotation is displayed as its own calendar. If one team has several rotations, those rotations are not mixed together.

Example:

```text
Team: Cloud
  Rotation: Cloud primary
  Rotation: Cloud secondary
```

The calendar renders them as separate schedules:

```text
Cloud primary
[calendar grid]

Cloud secondary
[calendar grid]
```

## What the calendar takes into account

The calendar uses the final schedule calculation:

- rotation layers;
- layer members;
- member order;
- layer priority;
- layer restrictions;
- layer timezone;
- handoff time;
- rotation duration;
- overrides.

Order of precedence:

```text
override > highest-priority active layer > no assignment
```

## Timeline view

Calendar cells use a timeline layout. Each on-call segment is placed inside the day according to its real duration.

Example:

```text
00:00      06:00      12:00      18:00      24:00
|----------|----------|----------|----------|
[ Ivan        ][ Petr ][ Anna                 ]
```

Only the on-call user is displayed inside the bar. Exact start/end time remains available in the hover title and details panel.

## Month view

Month view shows a compact timeline inside each day cell.

Use month view for team or rotation-level planning.

## Week view

Week view shows wider timeline rows and is useful for checking shift boundaries, night coverage and weekend coverage.

## Layers in the calendar

The calendar displays the winning final layer for every time segment.

For example:

```text
Business hours layer: Monday-Friday 09:00-18:00
Night layer:          Monday-Friday 18:00-09:00
Weekend layer:        Saturday-Sunday 00:00-00:00
```

The calendar will split the day into separate bars when the final on-call user changes.

## Overrides in the calendar

Overrides replace the calculated layer result for their time window.

Example:

```text
09:00-12:00 Ivan from Business hours layer
12:00-14:00 Anna from override
14:00-18:00 Ivan from Business hours layer
```

## Opening a specific rotation calendar

When you open a team that has several rotations, choose the required rotation from the rotation selector. Only one rotation calendar is shown at a time.

The URL can include a rotation id:

```text
/calendar?team_id=1&rotation_id=3
```

## No active layer

If no layer is active for a period, the calendar shows no on-call assignment for that period.

Common causes:

- layer is disabled;
- layer has no members;
- restrictions do not cover the selected time;
- timezone or handoff time is not configured as expected.

## Best practices

- Keep layer names clear: `Business hours`, `Nights`, `Weekend`, `Secondary`.
- Use restrictions instead of creating many separate rotations for the same duty line.
- Use separate rotations when they represent separate calendars, for example primary and secondary.
- Check the calendar after changing layer priority or restrictions.
- Use overrides for temporary changes, not for permanent schedule design.
