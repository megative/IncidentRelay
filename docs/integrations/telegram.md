---
title: Telegram Integration
description: Telegram Bot notifications, interactive ACK/Resolve buttons, polling, proxy setup, and troubleshooting
---

# Telegram Integration

IncidentRelay can send alert notifications through the Telegram Bot API.

Telegram channels support:

- alert notifications;
- inline `Acknowledge` and `Resolve` buttons;
- updating an existing Telegram message after an alert is acknowledged or resolved;
- polling Telegram callback actions through `getUpdates`.

Interactive buttons require Telegram polling and a linked Telegram user ID.

---

## Requirements

Create a Telegram bot with [BotFather](https://t.me/BotFather) and save the bot token.

The token looks like this:

```text
123456789:AA...
```

Treat the bot token as a secret.

If the token was written to logs, rotate it in BotFather.

---

## Channel configuration

Create a notification channel with type:

```text
telegram
```

Example channel config:

```json
{
  "bot_token": "123456789:AA...",
  "chat_id": "@team_alerts",
  "actions_enabled": true,
  "polling_enabled": true
}
```

Field meaning:

| Field | Required | Description |
|---|---:|---|
| `bot_token` | yes | Telegram bot token from BotFather. |
| `chat_id` | yes | Telegram chat, group, channel, or username target. |
| `actions_enabled` | no | Enables inline `Acknowledge` and `Resolve` buttons. Defaults to `true`. |
| `polling_enabled` | no | Enables polling for Telegram callback actions. Defaults to `true`. |

If `actions_enabled` is disabled, IncidentRelay sends plain Telegram messages without action buttons.

If `polling_enabled` is disabled, IncidentRelay can still send messages, but Telegram buttons will not be processed by the polling worker.

---

## Telegram user ID

For interactive actions, IncidentRelay must know which IncidentRelay user clicked a Telegram button.

Use Telegram `from.id` as the user's Telegram ID.

Do not use the group or channel `chat.id` as the user ID.

Send a message to the bot:

```text
/start
```

Then check updates:

```bash
curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getUpdates"
```

If the server uses an HTTP proxy:

```bash
curl -x http://proxy.example.com:3128 \
  "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getUpdates"
```

Look for `message.from.id`:

```json
{
  "message": {
    "from": {
      "id": 123456789,
      "is_bot": false,
      "username": "example_user"
    },
    "chat": {
      "id": 123456789
    }
  }
}
```

Use this value:

```text
123456789
```

For messages from a group or channel, `chat.id` can look like this:

```text
-1001234567890
```

That is the group or channel ID, not the user ID.

---

## Link Telegram user to IncidentRelay

Open the IncidentRelay user profile or user administration page and set the user's Telegram ID.

Use the Telegram `from.id` value.

If a Telegram user is not linked and clicks an action button, IncidentRelay returns:

```text
Telegram user is not linked to IncidentRelay
```

Fix:

1. Get the Telegram `from.id`.
2. Open the IncidentRelay user profile or admin user page.
3. Set the user's Telegram ID.
4. Click the Telegram button again.

---

## ACK and Resolve buttons

When actions are enabled, IncidentRelay adds inline buttons to Telegram alert messages.

Button behavior:

| Alert status | Buttons |
|---|---|
| `firing` | `Acknowledge`, `Resolve` |
| `acknowledged` | `Resolve` |
| `resolved` | no buttons |

After an action is processed, IncidentRelay updates the original Telegram message.

Telegram may return this response when the message already has the same text and buttons:

```text
Bad Request: message is not modified
```

IncidentRelay treats this as a harmless no-op.

---

## Polling mode

Telegram actions use `getUpdates` polling.

Telegram does not allow `getUpdates` while a webhook is active for the same bot token.

Check webhook status:

```bash
curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getWebhookInfo"
```

Delete webhook manually if needed:

```bash
curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/deleteWebhook"
```

Drop old pending updates if needed:

```bash
curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/deleteWebhook?drop_pending_updates=true"
```

If the server uses an HTTP proxy:

```bash
curl -x http://proxy.example.com:3128 \
  -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/deleteWebhook"
```

Do not use the same bot token for another service that depends on Telegram webhooks.

---

## Proxy setup

Telegram integration uses `pyTelegramBotAPI` / `telebot`.

IncidentRelay configures Telegram proxy globally through `telebot.apihelper.proxy`.

Set the proxy URL in the IncidentRelay config:

```ini
[telegram]
proxy_url = http://proxy.example.com:3128
```

For a normal HTTP Squid proxy, use `http://`:

```ini
[telegram]
proxy_url = http://proxy.example.com:3128
```

For a normal HTTP proxy, use `http://` even for HTTPS requests to Telegram. HTTPS traffic will go through the proxy by using HTTP `CONNECT`.

Do not use this for Squid:

```ini
[telegram]
proxy_url = socks5://proxy.example.com:3128
```

If you really use a SOCKS proxy, install SOCKS support:

```bash
pip install "requests[socks]"
```

or:

```bash
pip install PySocks
```

The same Telegram proxy setting is used for:

- sending Telegram alert messages;
- updating Telegram messages after ACK or Resolve;
- polling Telegram callback actions with `getUpdates`;
- answering Telegram callback queries.

After changing the proxy setting, restart all processes that use Telegram:

```bash
systemctl restart incidentrelay
systemctl restart incidentrelay-telegram-worker
systemctl restart incidentrelay-scheduler
```

Use only the services that exist in your installation.

---

## Test Telegram access

Direct connection:

```bash
curl -v "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getMe"
```

Through Squid:

```bash
curl -v -x http://proxy.example.com:3128 \
  "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getMe"
```

For HTTPS through an HTTP proxy, curl should use:

```text
CONNECT api.telegram.org:443
```

---

## Troubleshooting

### `Telegram user is not linked to IncidentRelay`

The Telegram button was clicked by a Telegram account that is not linked to any IncidentRelay user.

Fix:

1. Get the Telegram `from.id`.
2. Set this ID on the IncidentRelay user.
3. Try the button again.

---

### `Conflict: can't use getUpdates method while webhook is active`

The bot token has an active Telegram webhook.

Fix:

```bash
curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/deleteWebhook"
```

Then restart the Telegram polling process.

---

### `Missing dependencies for SOCKS support`

The proxy URL uses `socks5://` or `socks5h://`, but Python SOCKS support is not installed.

For Squid, use:

```ini
[telegram]
proxy_url = http://proxy.example.com:3128
```

For a real SOCKS proxy, install:

```bash
pip install "requests[socks]"
```

---

### `Network is unreachable`

The service cannot reach Telegram directly.

Fix:

1. Check server egress firewall rules.
2. Check DNS resolution for `api.telegram.org`.
3. Configure `[telegram] proxy_url` if Internet access is only available through a proxy.
4. Restart the IncidentRelay processes.

---

### `message is not modified`

Telegram says the edited message already has the same text and buttons.

This is harmless and usually means the action was already reflected in the message.
