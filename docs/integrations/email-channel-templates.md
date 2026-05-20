---
title: Email channel templates
description: HTML template syntax for IncidentRelay email channels
---

# Email channel templates

Email channels can override the default HTML body with `config.html_template`.

Email delivery uses the global SMTP transport. Recipients are not configured in the channel. Real alert emails are sent to the assigned user's profile email.

## Minimal config

Use the built-in default template:

```json
{}
```

Use the built-in default template only for critical and high alerts:

```json
{
  "notify_on_severities": ["critical", "high"]
}
```

## Custom template example

```json
{
  "html_template": "<h1>{event_type}: {title}</h1><p>{message}</p><table><tr><td>Severity</td><td>{severity}</td></tr><tr><td>Team</td><td>{team}</td></tr></table><p><a href=\"{alert_url}\">Open alert</a></p>"
}
```

## Placeholder syntax

Use Python format-style placeholders:

```text
{title}
{message}
{severity}
```

Do not use mustache-style placeholders unless the renderer is explicitly changed to support them:

```text
{{ title }}
```

## Supported placeholders

| Placeholder | Description |
|---|---|
| `{alert_id}` | IncidentRelay alert ID |
| `{event_type}` | Notification event |
| `{title}` | Alert title |
| `{message}` | Alert message |
| `{severity}` | Alert severity |
| `{status}` | Alert status |
| `{team}` | Team slug |
| `{assignee}` | Assigned user display name or username |
| `{source}` | Alert source |
| `{alert_url}` | Link to the alert in the IncidentRelay UI |

## Safety

Alert values are HTML-escaped before insertion into the template. This lets users customize layout without turning alert labels or annotations into raw HTML.

## Troubleshooting

### The email contains only `resolved` or `notification`

The channel probably has a broken `html_template` saved in its config. Reset the template in the Channels UI or remove the `html_template` key from the channel config.

### The email shows `{title}` instead of the real title

The renderer and template placeholder syntax are out of sync. The default template uses `{title}` style placeholders, so rendering must use Python format-style replacement.
