---
title: Rotation Overrides
description: Temporarily replace normal on-call duty
---

# Rotation Overrides

A rotation override temporarily replaces the normal on-call user for a selected rotation and time range.

Use it when someone is on vacation, sick, unavailable, or when another engineer needs to cover a specific period.

## Create an override in the web UI

Open:

```text
Rotations
```

In the `Create override` block:

1. Select a rotation.
2. Select the user who should cover the duty.
3. Set `Starts at`.
4. Set `Ends at`.
5. Optionally write a reason.
6. Click `Create override`.

The override appears in the `Overrides` table.

You can also click `Overrides` next to a rotation in the rotations table to load its override list.

## Delete an override

Open:

```text
Rotations
```

Select the rotation or click `Overrides`, then click `Delete` next to the override.

## API

Create override:

```bash
curl -X POST http://127.0.0.1:8080/api/rotations/1/overrides \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer JWT_TOKEN' \
  -d '{
    "user_id": 2,
    "starts_at": "2026-05-01T09:00:00",
    "ends_at": "2026-05-02T09:00:00",
    "reason": "Vacation cover"
  }'
```

List overrides:

```bash
curl -H 'Authorization: Bearer JWT_TOKEN' \
  http://127.0.0.1:8080/api/rotations/1/overrides
```

Delete override:

```bash
curl -X DELETE \
  -H 'Authorization: Bearer JWT_TOKEN' \
  http://127.0.0.1:8080/api/rotations/overrides/10
```
