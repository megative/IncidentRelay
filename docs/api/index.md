# API

Swagger UI is available at:

```text
/docs
```

OpenAPI JSON is available at:

```text
/api/openapi.json
```

Use route intake tokens for incoming integration endpoints and personal API tokens for user-scoped automation.

## Browser push API

Browser push profile endpoints are user-scoped and require authentication:

```text
GET    /api/profile/push/vapid-public-key
GET    /api/profile/push/subscriptions
POST   /api/profile/push/subscriptions
DELETE /api/profile/push/subscriptions/{subscription_id}
POST   /api/profile/push/test
```

Push notification action endpoint is public by design and uses a one-time action token from the notification payload:

```text
POST /api/push/actions
```

Read more: [Browser Push](../usage/browser-push.md).

## Services API

Service management endpoints are available under:

```text
/api/services
```

They cover:

- services;
- service match rules;
- service links;
- service runbooks;
- service dependencies;
- service analytics;
- service impact.

Services describe the logical affected system.

Routes answer how an alert entered IncidentRelay, and services answer what system is broken.

Common service endpoints:

```text
GET /api/services
POST /api/services
GET /api/services/{service_id}
PUT /api/services/{service_id}
DELETE /api/services/{service_id}
```

Service match rules:

```text
GET /api/services/match-rules
GET /api/services/{service_id}/match-rules
POST /api/services/{service_id}/match-rules
PUT /api/services/match-rules/{rule_id}
DELETE /api/services/match-rules/{rule_id}
```

Service links and runbooks:

```text
GET /api/services/links
GET /api/services/{service_id}/links
POST /api/services/{service_id}/links
GET /api/services/runbooks
GET /api/services/{service_id}/runbooks
POST /api/services/{service_id}/runbooks
```

Analytics and impact:

```text
GET /api/services/analytics
GET /api/services/impact
```

Display order for service and team names in API consumers and UI:

```text
name -> slug -> "-"
```

## More API documentation

1. [Voice API](voice-api.md)
2. [Escalation policy](escalation-policies.md)
