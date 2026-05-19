# Email channel templates

Email delivery uses the global SMTP transport from the IncidentRelay configuration. Email channels do not store SMTP host, port, username, password, TLS, or sender settings.

An email channel config controls only delivery recipients, optional severity filters, and an optional HTML template override.

```json
{
  "recipients": ["sre@example.com", "noc@example.com"],
  "notify_on_severities": ["critical", "high"],
  "html_template": "<h1>{title}</h1><p>{message}</p>"
}
```

If `html_template` is omitted or empty, IncidentRelay uses the built-in default HTML template. The Channels UI shows this default template when configuring an email channel, so it can be copied or customized.

Supported placeholders:

- `{alert_id}`
- `{event_type}`
- `{title}`
- `{message}`
- `{severity}`
- `{status}`
- `{team}`
- `{assignee}`
- `{source}`
- `{alert_url}`

Alert values are HTML-escaped before they are inserted into the template. Unknown placeholders are left unchanged.
