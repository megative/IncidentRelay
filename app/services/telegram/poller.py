import logging
from datetime import datetime

from app.db import database_proxy as db
from app.modules.db import alerts_repo, channels_repo, users_repo
from app.services.alerts import acknowledge_alert, resolve_alert
from app.services.telegram.templates import format_telegram_alert_message
from app.services.telegram.actions import parse_telegram_action_data
from app.services.telegram.bot import (
    answer_telegram_callback,
    get_telegram_bot,
    update_telegram_alert,
)


logger = logging.getLogger("oncall.telegram")

_channel_offsets = {}


def list_polling_telegram_channels():
    """
    Return enabled Telegram channels with action polling enabled.
    """
    channels = channels_repo.list_channels(enabled_only=True)

    return [
        channel
        for channel in channels
        if channel.channel_type == "telegram"
        and (channel.config or {}).get("polling_enabled", True)
        and (channel.config or {}).get("actions_enabled", True)
        and (channel.config or {}).get("bot_token")
    ]


def poll_telegram_channels_once(timeout=20):
    """
    Poll all Telegram channels once.
    """
    processed = 0

    for channel in list_polling_telegram_channels():
        processed += poll_telegram_channel_once(channel, timeout=timeout)

    return processed


def poll_telegram_channel_once(channel, timeout=20):
    """
    Poll one Telegram channel with getUpdates.
    """
    config = channel.config or {}
    bot = get_telegram_bot(config.get("bot_token"))
    offset = _channel_offsets.get(channel.id)

    updates = bot.get_updates(
        offset=offset,
        timeout=timeout,
        allowed_updates=["callback_query"],
    )

    processed = 0

    for update in updates:
        _channel_offsets[channel.id] = update.update_id + 1

        if not update.callback_query:
            continue

        handle_telegram_callback(channel, update.callback_query)
        processed += 1

    return processed


def handle_telegram_callback(channel, callback):
    """
    Handle Telegram ACK/Resolve callback.
    """
    if db.is_closed():
        db.connect(reuse_if_open=True)

    try:
        action_data = parse_telegram_action_data(callback.data)

        if not action_data:
            answer_telegram_callback(
                channel,
                callback.id,
                "Invalid action",
                show_alert=True,
            )
            return

        if int(action_data["channel_id"]) != int(channel.id):
            answer_telegram_callback(
                channel,
                callback.id,
                "Action belongs to another channel",
                show_alert=True,
            )
            return

        telegram_user_id = str(callback.from_user.id)
        user = users_repo.get_user_by_telegram_id(telegram_user_id)

        if not user:
            answer_telegram_callback(
                channel,
                callback.id,
                "Telegram user is not linked to IncidentRelay",
                show_alert=True,
            )
            return

        alert_id = int(action_data["alert_id"])
        action = action_data["action"]

        if action == "acknowledge":
            alert = acknowledge_alert(alert_id, user_id=user.id)
            event_type = "acknowledged"
            answer_text = f"Alert #{alert.id} acknowledged"
        elif action == "resolve":
            alert = resolve_alert(alert_id, user_id=user.id)
            event_type = "resolved"
            answer_text = f"Alert #{alert.id} resolved"
        else:
            answer_telegram_callback(
                channel,
                callback.id,
                "Unsupported action",
                show_alert=True,
            )
            return

        alerts_repo.create_alert_event(
            alert.id,
            f"telegram_{event_type}",
            f"Telegram action by {user.username}",
        )

        update_telegram_alert(
            channel=channel,
            alert=alert,
            text=format_telegram_alert_message(alert, event_type, actor=user),
            delivery=type("TelegramDelivery", (), {
                "external_channel_id": str(callback.message.chat.id),
                "external_message_id": str(callback.message.message_id),
            })(),
            event_type=event_type,
        )

        answer_telegram_callback(channel, callback.id, answer_text)

        logger.info(
            "telegram action processed",
            extra={
                "extra": {
                    "event_type": "telegram_action",
                    "alert_id": alert.id,
                    "channel_id": channel.id,
                    "action": action,
                    "user_id": user.id,
                    "telegram_user_id": telegram_user_id,
                    "processed_at": datetime.utcnow().isoformat(),
                }
            },
        )

    except Exception as exc:
        logger.exception(
            "telegram callback failed",
            extra={
                "extra": {
                    "channel_id": channel.id,
                    "callback_id": getattr(callback, "id", None),
                    "error": str(exc),
                }
            },
        )

        try:
            answer_telegram_callback(
                channel,
                callback.id,
                "IncidentRelay action failed",
                show_alert=True,
            )
        except Exception:
            logger.exception("failed to answer telegram callback after error")
