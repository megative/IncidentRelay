# Route Intake Tokens

Incoming integrations authenticate with route intake tokens.

A token belongs to a route, not to a channel.

```text
Monitoring system -> Integration endpoint -> Route token -> Route -> Channels
```

## Why tokens belong to routes

A route defines:

- source type, such as `alertmanager`, `zabbix` or `webhook`;
- team;
- rotation;
- matchers;
- attached notification channels;
- grouping behavior.

The token identifies which route should receive incoming alerts.

## Usage

Use the token in the incoming integration request, for example:

```text
Authorization: Bearer ROUTE_TOKEN
```

Do not put route tokens into notification channel configuration.

## Regeneration

If a route token is lost or exposed, regenerate it from the Routes page and update the monitoring system configuration.

After regeneration, the old token should stop working.
