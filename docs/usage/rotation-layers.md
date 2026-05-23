---
title: Rotation Layers
description: Layered on-call schedules, restrictions and final schedule calculation
---

# Rotation Layers

Rotation layers allow one rotation to contain several schedule rules.

Use layers when one duty line needs different coverage windows, for example:

- business hours;
- nights;
- weekends;
- primary and secondary duties;
- regional schedules with different timezones.

## Basic model

```text
Rotation
  Layer: Business hours
    Members: Ivan -> Petr -> Anna
    Restrictions: Monday-Friday 09:00-18:00

  Layer: Nights
    Members: Petr -> Anna -> Ivan
    Restrictions: Monday-Friday 18:00-09:00

  Layer: Weekend
    Members: Anna -> Ivan -> Petr
    Restrictions: Saturday-Sunday 00:00-00:00
```

The rotation produces one final on-call user for a given time.

## Layer fields

A layer has:

- name;
- priority;
- enabled flag;
- start date/time;
- rotation type: daily, weekly or custom;
- handoff time;
- handoff weekday for weekly rotations;
- timezone;
- ordered members;
- optional restrictions.

## Members

Layer members are ordered by position.

Example:

```text
Position 0: Ivan
Position 1: Petr
Position 2: Anna
```

The selected user changes according to the layer cadence and handoff settings.

## Restrictions

Restrictions define when a layer is active.

If a layer has no restrictions, it is active 24/7.

Examples:

```text
Monday-Friday 09:00-18:00
Monday-Friday 18:00-09:00
Saturday 00:00-00:00
Sunday 00:00-00:00
```

`00:00-00:00` means full day.

Restrictions are interpreted in the layer timezone.

## Priority

If multiple layers are active at the same time, the higher priority layer wins.

Example:

```text
Business hours: priority 10
Weekend:        priority 30
```

If both match, `Weekend` wins because it has higher priority.

## Overrides

Overrides always win over layer calculation.

Final order:

```text
override > highest-priority active layer > no assignment
```

## Presets

The UI may provide presets for common restrictions:

```text
24/7
Business hours
Nights
Weekend
```

Presets only create normal restriction rows. You can edit them after applying the preset.

## Timezone behavior

Use the layer timezone for recurring rules.

Example:

```text
Timezone: Europe/Berlin
Restriction: Monday-Friday 09:00-18:00
```

The restriction means 09:00-18:00 in Berlin local time. UTC offsets may change because of daylight saving time.

## Best practices

- Use one rotation for one duty line.
- Use layers for different active windows inside the same duty line.
- Use separate rotations when you need separate calendars, for example primary and secondary.
- Keep priorities spaced, for example 10, 20, 30.
- Verify the final result in the calendar after changing restrictions.
