---
title: Troubleshooting
description: Common IncidentRelay troubleshooting steps
---

# Troubleshooting

## Alert is not visible

If an alert is not visible:

1. Check that the correct route intake token was used.
2. Check that the endpoint matches the route source.
3. Check that route matchers match alert labels.
4. Check that the group is active.
5. Check that the team is active.
6. Check that the top right active group is correct.
7. Select `All my groups` and reload the Alerts page.

The webhook response includes:

```text
route_id
rotation_id
routing_error
```

## Route source mismatch

The endpoint must match the route `source`.

```text
route.source = alertmanager -> POST /api/integrations/alertmanager
route.source = webhook      -> POST /api/integrations/webhook
route.source = zabbix       -> POST /api/integrations/zabbix
```

If the route token belongs to an `alertmanager` route and you send the request to `/api/integrations/webhook`, the service returns:

```json
{
  "routing_error": "route source 'alertmanager' does not match alert source 'webhook'"
}
```

## Mattermost buttons do not work

Check:

```text
- public_base_url is reachable from Mattermost.
- Mattermost channel uses Bot API mode.
- Mattermost bot token is valid.
- Mattermost channel_id is correct.
- action_secret / callback secret is correct.
```

## Voice callbacks do not work

Check:

```text
- public_base_url is reachable from the voice provider.
- Callback URL contains the correct channel_id.
- Callback URL contains the correct callback secret.
- Channel type is voice_call.
- Provider sends JSON or form data supported by parse_callback().
```

See [Voice Provider Troubleshooting](../voice-providers/troubleshooting.md).
