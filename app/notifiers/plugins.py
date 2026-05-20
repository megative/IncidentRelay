import logging

import requests

from app.notifiers.base import BaseNotifier
from app.services.links import build_alert_web_url

logger = logging.getLogger("oncall.alerts")


class IncomingWebhookNotifier(BaseNotifier):
    """Send notifications through a generic incoming webhook."""

    name = "webhook"

    def send(self, channel, alert, text, event_type="notification"):
        """Send a JSON webhook notification."""
        config = channel.config or {}
        webhook_url = config.get("webhook_url")
        if not webhook_url:
            raise RuntimeError("webhook_url is missing")

        response = requests.post(
            webhook_url,
            json={
                "text": text,
                "alert_id": alert.id,
                "alert_url": build_alert_web_url(alert),
                "team": alert.team.slug if alert.team else None,
                "status": alert.status,
                "source": alert.source,
                "title": alert.title,
                "message": alert.message,
                "severity": alert.severity,
                "assignee": alert.assignee.username if alert.assignee else None,
            },
            timeout=10,
        )
        response.raise_for_status()
        return {"provider": self.name}


class SlackNotifier(IncomingWebhookNotifier):
    """Send notifications through Slack Incoming Webhook."""

    name = "slack"


class TeamsNotifier(IncomingWebhookNotifier):
    """Send notifications through Microsoft Teams Incoming Webhook."""

    name = "teams"


class DiscordNotifier(IncomingWebhookNotifier):
    """Send notifications through Discord Webhook."""

    name = "discord"

    def send(self, channel, alert, text, event_type="notification"):
        """Send a Discord webhook notification."""
        config = channel.config or {}
        webhook_url = config.get("webhook_url")
        if not webhook_url:
            raise RuntimeError("webhook_url is missing")

        response = requests.post(webhook_url, json={"content": text}, timeout=10)
        response.raise_for_status()
        return {"provider": self.name}


