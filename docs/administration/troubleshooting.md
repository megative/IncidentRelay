# Troubleshooting

## 500 on duplicate names or slugs

Duplicate resources should return `409 Conflict`, not `500`.

Check API logs for `IntegrityError` and add explicit error handling in the corresponding view.

Common examples:

- duplicate group slug;
- duplicate team slug;
- duplicate channel name inside the same team.

## Empty body returns unclear validation error

POST/PUT endpoints should return a structured `400 validation_error` when body is missing or invalid JSON.

## Calendar invalid date returns 500

Query parameters such as `start` and `end` should be validated before date parsing reaches business logic.

## Email test works but real alert does not

Check:

1. Real alert has an assignee.
2. Assigned user has email in profile.
3. Channel is attached to the matched route.
4. Severity filter allows the alert severity.
5. SMTP relay accepted and delivered the message.

## Voice call fails with missing phone

Voice call sends to the assigned user's profile phone number. Set `phone` on the assigned user.

## Telegram token error

Telegram bot token must contain a colon:

```text
123456789:AA...
```

If the token is invalid, fix the channel config or disable the channel.

## Reminders are duplicated

Check that only one scheduler process is running and that scheduler is not started inside every web worker.
