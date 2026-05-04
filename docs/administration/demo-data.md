---
title: Demo Data
description: Create and validate IncidentRelay demo data
---

# Demo Data

Create demo data:

```bash
python manage.py demo-data
```

The command creates:

- admin user `admin` with password `admin123`;
- admin is not attached to any group and has no active group;
- `infra` group and `database` group;
- regular demo users with password `changeme123`;
- regular users are added to their group with `rw` role;
- regular users have `active_group` set;
- teams, rotations, channels, and alert routes;
- route intake tokens for Alertmanager routes.

Static demo-data check:

```bash
python app/check_demo_data.py
```

Expected output:

```text
Demo data check OK.
```

## create-admin group behavior

`python manage.py create-admin` creates or updates an administrator without group memberships and without active_group.

If the username already existed as a regular user, existing group memberships are disabled.
