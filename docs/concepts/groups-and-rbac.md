---
title: Groups and RBAC
description: Access groups and group roles
---

# Groups and RBAC

## Group

A group is an access boundary.

All teams belong to a group. Users only see resources from groups they belong to. A user can belong to multiple groups.

## Group role

A user can have one of these roles inside a group:

```text
read_only
rw
```

`read_only` can view resources and alerts.

`rw` can create, edit, acknowledge, and resolve resources in that group.

Admin users can see and manage everything.

## Active group

Users can choose their active group from Profile.

Active group limits resource lists in the UI.

To see all accessible resources, select:

```text
All my groups
```

## Editing memberships

The web UI supports editing and disabling memberships:

```text
Administration -> Groups -> Members
Teams -> Members
Rotations -> Members
```

For group and team memberships you can change:

```text
role
active flag
```

For rotation members you can change:

```text
position
active flag
```

Disabling a membership keeps historical records intact.
