---
title: Mattermost Integration
description: Mattermost notification modes and action buttons
---

# Mattermost Integration

Mattermost has two modes.

## Incoming webhook mode

This mode sends plain messages only.

It cannot:

- show buttons;
- update messages after acknowledge;
- update messages after resolve.

## Bot API mode

This mode is recommended.

It supports:

- `Acknowledge` button;
- `Resolve` button;
- message updates;
- colored attachment borders.

Example channel settings:

```text
Type: mattermost
Mode: Bot API with buttons and message updates
Mattermost URL: https://mattermost.example.com
Bot token: <bot-token>
Channel ID: <mattermost-channel-id>
Callback secret: optional
```

## Colors

```text
critical/high/error -> red
warning/acknowledged -> yellow
info -> blue
resolved -> green
```

After `Acknowledge`, the original Mattermost message is updated and keeps only the `Resolve` button.

After `Resolve`, the original Mattermost message is updated, the buttons are removed, and the border becomes green.

## public_base_url vs Mattermost URL

`public_base_url` is the public URL of IncidentRelay itself.

Mattermost uses this URL when a user clicks buttons such as `Acknowledge` or `Resolve`.

The button callback URL is built like this:

```text
https://incidentrelay.example.com/api/integrations/mattermost/actions
```

The Mattermost URL in a Mattermost channel is the URL of the Mattermost server API.

```text
https://mattermost.example.com
```

IncidentRelay uses it to send and update Mattermost posts through the Bot API.

In short:

```text
public_base_url = where Mattermost calls IncidentRelay back
Mattermost URL = where IncidentRelay sends messages to Mattermost
```

For Mattermost buttons to work, `public_base_url` must be reachable from the Mattermost server.
