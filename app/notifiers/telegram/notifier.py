from app.notifiers.base import BaseNotifier
from app.notifiers.telegram.bot import send_telegram_alert, update_telegram_alert
from app.notifiers.telegram.templates import format_telegram_alert_message


class TelegramNotifier(BaseNotifier):
    """Send and update Telegram notifications."""

    name = "telegram"
    supports_update = True

    def send(self, channel, alert, text, event_type="notification"):
        """Send a formatted Telegram alert message."""
        telegram_text = format_telegram_alert_message(alert, event_type)
        return send_telegram_alert(channel, alert, telegram_text, event_type)

    def update(self, channel, alert, text, delivery, event_type="resolved"):
        """Update a formatted Telegram alert message."""
        telegram_text = format_telegram_alert_message(alert, event_type)
        return update_telegram_alert(
            channel,
            alert,
            telegram_text,
            delivery,
            event_type,
        )
