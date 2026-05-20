---
title: Telegram notification channel
description: Telegram Bot API notifications, inline actions, polling, proxy setup, and troubleshooting
---

# Telegram notification channel

IncidentRelay can send alert notifications through the Telegram Bot API.

Telegram channels support:

- alert notifications;
- inline `Acknowledge` and `Resolve` buttons;
- updating an existing Telegram message after ACK or Resolve;
- polling Telegram callback actions through `getUpdates`.

## Requirements

Create a Telegram bot with [BotFather](https://t.me/BotFather) and save the bot token.

The token must contain a colon:

```text
123456789:AA...
```

Treat the bot token as a secret. If the token was written to logs, rotate it in BotFather.

## Channel config

```json
{
  "bot_token": "123456789:AA...",
  "chat_id": "@team_alerts",
  "actions_enabled": true,
  "polling_enabled": true
}
```

With severity filter:

```json
{
  "bot_token": "123456789:AA...",
  "chat_id": "@team_alerts",
  "actions_enabled": true,
  "polling_enabled": true,
  "notify_on_severities": ["critical", "high"]
}
```

| Field | Required | Description |
|---|---:|---|
| `bot_token` | Yes | Telegram bot token from BotFather |
| `chat_id` | Yes | Chat, group, channel, or username target |
| `actions_enabled` | No | Enables inline ACK/Resolve buttons |
| `polling_enabled` | No | Enables polling callback actions with `getUpdates` |

If `actions_enabled` is disabled, IncidentRelay sends plain Telegram messages without action buttons. If `polling_enabled` is disabled, buttons may be visible but callback actions will not be processed by the polling worker.

## Telegram user ID

For interactive actions, IncidentRelay must know which IncidentRelay user clicked a Telegram button.

Use Telegram `from.id` as the user's Telegram ID. Do not use the group or channel `chat.id` as the user ID.

Send a message to the bot:

```text
/start
```

Then check updates:

```bash
curl "https://api.telegram.org/bot<TOKEN>/getUpdates"
```

Look for:

```json
{
  "message": {
    "from": {
      "id": 123456789,
      "is_bot": false,
      "username": "example_user"
    },
    "chat": {
      "id": -1001234567890
    }
  }
}
```

Use `message.from.id`, not `message.chat.id`.

## Link Telegram user to IncidentRelay

Open the IncidentRelay user profile or user administration page and set the user's Telegram ID.

If a Telegram user is not linked and clicks an action button, IncidentRelay returns:

```text
Telegram user is not linked to IncidentRelay
```

## Polling mode

Telegram actions use `getUpdates` polling. Telegram does not allow `getUpdates` while a webhook is active for the same bot token.

Check webhook status:

```bash
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

Delete webhook if needed:

```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/deleteWebhook"
```

Drop old pending updates if needed:

```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/deleteWebhook?drop_pending_updates=true"
```

## Proxy setup

Telegram integration uses `pyTelegramBotAPI` / `telebot`. Configure the Telegram proxy globally in the IncidentRelay config:

```ini
[telegram]
proxy_url = http://proxy.example.com:3128
```

For a normal HTTP Squid proxy, use `http://`, even for HTTPS requests to Telegram. HTTPS traffic goes through the proxy using HTTP `CONNECT`.

Do not use this for Squid:

```ini
[telegram]
proxy_url = socks5://proxy.example.com:3128
```

If you really use a SOCKS proxy, install SOCKS support:

```bash
pip install "requests[socks]"
```

After changing proxy settings, restart processes that use Telegram, such as the web service, scheduler, and Telegram worker.

## Troubleshooting

### `Token must contain a colon`

The bot token is invalid or truncated. Replace it with the BotFather token format:

```text
123456789:AA...
```

### `Conflict: can't use getUpdates method while webhook is active`

Delete the Telegram webhook for this bot token and restart the Telegram polling process.

### `message is not modified`

Telegram says the edited message already has the same text and buttons. IncidentRelay can treat this as a harmless no-op.

### `Network is unreachable`

Check server egress firewall rules, DNS, and `[telegram] proxy_url`.
