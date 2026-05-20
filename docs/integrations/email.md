---
title: Email notification channel
description: Configure email notifications and HTML templates
---

# Email notification channel

Email channels send alert emails through the globally configured SMTP transport.

## Recipient model

Real alert email is sent to the assigned user's profile email.

```text
Route -> Rotation -> Current assignee -> assignee.email -> SMTP
```

Required user field:

```text
User profile -> email
```

If the assigned user has no email address, the email notifier cannot send the alert and returns an error similar to:

```text
email recipient is missing: set email on the assigned user
```

## Channel config

Minimal email channel config:

```json
{}
```

Email channel with severity filter:

```json
{
  "notify_on_severities": ["critical", "high"]
}
```

Email channel with a custom HTML template:

```json
{
  "notify_on_severities": ["critical", "high"],
  "html_template": "<h1>{event_type}: {title}</h1><p>{message}</p><p><a href=\"{alert_url}\">Open alert</a></p>"
}
```

## Global SMTP configuration

SMTP is configured by the system administrator in the IncidentRelay config file.

Example:

```ini
[smtp]
host = smtp.example.com
port = 587
from = incidentrelay@example.com
use_tls = true
user = incidentrelay@example.com
password = change-me
```

For an unauthenticated local relay, leave `user` and `password` empty:

```ini
[smtp]
host = 127.0.0.1
port = 25
from = incidentrelay@example.com
use_tls = false
user =
password =
```

Do not put SMTP transport settings into channel config.

## HTML templates

The Channels UI shows the built-in default HTML template. Leave it unchanged to use the built-in layout, or edit it to override the email body for that channel.

Supported placeholders use Python format style:

| Placeholder | Description |
|---|---|
| `{alert_id}` | IncidentRelay alert ID |
| `{event_type}` | Notification event, for example `NOTIFICATION`, `ACKNOWLEDGED`, or `RESOLVED` |
| `{title}` | Alert title |
| `{message}` | Alert message |
| `{severity}` | Alert severity |
| `{status}` | Alert status |
| `{team}` | Team slug |
| `{assignee}` | Assigned user display name or username |
| `{source}` | Alert source |
| `{alert_url}` | Link to the alert in the IncidentRelay UI |

Alert values are HTML-escaped before insertion into the template. Unknown placeholders should remain unchanged instead of breaking notification delivery.

See also: [Email templates](email-channel-templates.md).

## Testing

The email channel test should send a test email to the current user's profile email. If the current user has no email, set it in the profile or user administration page first.

## Troubleshooting

### Test email works, real alert email does not

Check:

1. The real alert has an assignee.
2. The assignee has `email` configured.
3. The email channel is attached to the matched route.
4. The channel severity filter allows the alert severity.
5. The alert is not silenced.

### `SMTP AUTH extension not supported by server`

The SMTP server does not support authentication, but `user` or `password` is configured. Clear both values for an unauthenticated relay or use an SMTP server that supports AUTH.

### Email body shows placeholders like `{title}`

The template was not rendered correctly. Check that the renderer uses the same placeholder style as the template: `{title}`, not `{{ title }}`.
