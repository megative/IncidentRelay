---
title: Rotation Overrides
description: Temporary replacements for the final on-call schedule
---

# Rotation Overrides

Rotation overrides temporarily replace the calculated on-call user.

Use overrides for:

- vacation;
- planned maintenance;
- shift swaps;
- one-off coverage changes;
- temporary absence.

## How overrides work

An override belongs to a rotation and has a time window.

When the calendar or alert assignment is calculated inside that time window, the override user is used instead of the normal final layer result.

Precedence:

```text
override > highest-priority active layer > no assignment
```

## Overrides and layers

Layers define the normal schedule. Overrides are temporary exceptions.

Example normal layer setup:

```text
Layer: Business hours
Members: Ivan -> Petr -> Anna
Active: Monday-Friday 09:00-18:00
```

Example override:

```text
User: Sergey
Window: 2026-05-25 12:00 -> 2026-05-25 16:00
Reason: Ivan is unavailable
```

During the override window, Sergey is shown in the calendar and used for alert assignment.

## Calendar behavior

The calendar splits affected shifts around the override window.

Example:

```text
09:00-12:00 Ivan
12:00-16:00 Sergey override
16:00-18:00 Ivan
```

## Deleting a rotation

When a rotation is deleted:

- the rotation is soft-deleted;
- its layers are soft-deleted;
- layer members and restrictions are removed;
- rotation overrides are removed;
- routes are kept, but their `rotation_id` is cleared.

## Best practices

- Keep override windows as short and precise as possible.
- Add a clear reason.
- Verify the calendar after creating an override.
- Remove or adjust incorrect overrides.
- Do not use overrides for permanent schedule patterns; use layers and restrictions instead.
