---
title: Profile and Personal API Tokens
description: User profile and personal API token access
---

# Profile and Personal API Tokens

Open Profile from the top right corner.

Users can:

- update display name;
- update email;
- update phone;
- set Telegram chat ID;
- set Slack user ID;
- set Mattermost user ID;
- change password;
- choose active group;
- create a personal API token.

Active group limits resource lists in the UI.

To see all accessible resources, select:

```text
All my groups
```

## Personal API tokens

Users can create personal API tokens in Profile.

The token value is shown only once.

Available scopes:

```text
alerts:read
alerts:write
resources:read
resources:write
profile:read
profile:write
*
```

## Using a personal API token

Personal API tokens can be used with regular API endpoints:

```bash
curl -H 'Authorization: Bearer PERSONAL_API_TOKEN' \
  http://127.0.0.1:8080/api/alerts
```

Scopes control what the token can do:

```text
alerts:read     read alerts
alerts:write    acknowledge, resolve, and submit alerts
resources:read  read teams, groups, rotations, routes, channels, silences, calendar
resources:write create or edit teams, groups, rotations, routes, channels, silences
profile:read    read profile
profile:write   edit profile
*               all scopes
```

If the token is created for a specific group, API responses are limited to that group.

If the token has no group restriction, it uses the same group access as the token owner.

For example, to read teams and routes, create the token with:

```text
resources:read
```

To read alerts, create the token with:

```text
alerts:read
```
