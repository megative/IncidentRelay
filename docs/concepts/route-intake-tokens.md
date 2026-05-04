---
title: Route Intake Tokens
description: How route intake tokens work
---

# Route Intake Tokens

Alert intake tokens belong to routes, not channels.

A route token identifies the exact alert path:

```text
Route token -> Route -> Team -> Rotation -> Notification channels
```

External systems should send alerts with the route token:

```bash
curl -X POST http://127.0.0.1:8080/api/integrations/alertmanager \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ROUTE_INTAKE_TOKEN' \
  -d '{...}'
```

Channels do not expose intake tokens. They are notification targets used by routes.

If you need a new token, open `Routes` and click `Regenerate token` next to the route.

## Route source validation

Incoming alerts are routed by the route intake token.

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
