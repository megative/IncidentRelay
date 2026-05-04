---
title: Channels
description: Notification channel types
---

# Channels

A channel is a notification destination.

Supported channel types:

```text
Mattermost
Slack
Telegram
Webhook
Discord
Teams
Email
Voice call
```

Channels do not have alert intake tokens.

A route receives alerts through its route intake token and then sends notifications to one or more channels.

## Mattermost

Mattermost has two modes:

- Incoming webhook mode
- Bot API mode

Bot API mode is recommended because it supports buttons and message updates.

## Voice call

Voice call channels can use built-in or custom providers.

Custom providers can implement:

- text-to-speech calls;
- call status callbacks;
- DTMF button callbacks;
- ACK / Resolve actions from phone keypad;
- optional call status polling.

See [Custom Voice Providers](../voice-providers/index.md).
