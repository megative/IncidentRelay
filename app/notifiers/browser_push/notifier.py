from app.notifiers.browser_push import service as browser_push


class BrowserPushNotifier:
    """Send alert notifications to assignee browser push subscriptions."""

    name = "browser_push"
    supports_update = False

    def send(self, channel, alert, text, event_type="notification"):
        assignee = getattr(alert, "assignee", None)

        if not assignee:
            return {
                "provider": "browser_push",
                "provider_status": "skipped",
                "skipped": True,
                "skip_reason": "no_assignee",
            }

        sent = browser_push.send_alert_push_to_user(
            assignee,
            alert,
            event_type=event_type,
        )

        if not sent:
            return {
                "provider": "browser_push",
                "provider_status": "skipped",
                "skipped": True,
                "skip_reason": "no_active_push_subscriptions",
            }

        return {
            "provider": "browser_push",
            "provider_status": "sent",
            "provider_payload": {
                "sent": sent,
                "assignee_id": assignee.id,
            },
        }
