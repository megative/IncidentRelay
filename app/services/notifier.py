import logging
from datetime import datetime

from app.settings import Config
from app.modules.db import alerts_repo, notifications_repo, routes_repo
from app.notifiers.registry import get_notifier
from app.services.severity import normalize_severity, normalize_severity_list


EDITABLE_EVENTS = {"acknowledged", "resolved"}
logger = logging.getLogger("oncall.notifications")


def format_alert_message(alert, event_type="notification"):
    """
    Format a plain text alert notification.
    """

    assignee = alert.assignee.display_name or alert.assignee.username if alert.assignee else "unknown"
    team = alert.team.slug if alert.team else "unknown"
    return (
        f"{event_type.upper()}: {alert.title}\n"
        f"Team: {team}\n"
        f"Status: {alert.status}\n"
        f"Severity: {alert.severity or '-'}\n"
        f"Assignee: {assignee}\n"
        f"Source: {alert.source}\n"
        f"Message: {alert.message or '-'}\n"
        f"ACK URL: {Config.PUBLIC_BASE_URL}/api/alerts/{alert.id}/ack"
    )


def get_channel_notify_on_severities(channel):
    """Return normalized channel-level severity filter.

    Empty list means that the channel accepts all severities.
    The legacy config key 'severities' is accepted for backward compatibility,
    but 'notify_on_severities' is the canonical key.
    """
    config = channel.config or {}
    raw_severities = config.get("notify_on_severities")

    if raw_severities is None:
        raw_severities = config.get("severities")

    try:
        return set(normalize_severity_list(raw_severities))
    except ValueError as exc:
        logger.warning(
            "invalid channel severity filter, ignoring it",
            extra={
                "extra": {
                    "channel_id": channel.id,
                    "channel_type": channel.channel_type,
                    "error": str(exc),
                }
            },
        )
        return set()


def channel_matches_alert_severity(channel, alert):
    """Return True when the channel should receive this alert severity."""
    allowed_severities = get_channel_notify_on_severities(channel)

    if not allowed_severities:
        return True

    alert_severity = normalize_severity(getattr(alert, "severity", None))
    return alert_severity in allowed_severities


def has_matching_notification_channel(alert):
    """Return True if the alert has at least one enabled channel
    that accepts the alert severity.

    Used by scheduler before reminder/escalation processing to avoid
    counting reminders for alerts that cannot be delivered to any channel.
    """
    if not alert.route:
        return False

    for link in routes_repo.list_route_channels(alert.route.id):
        channel = link.channel

        if not channel.enabled:
            continue

        if channel_matches_alert_severity(channel, alert):
            return True

    return False


def notify_alert(alert, event_type="notification"):
    """
    Send or update alert notifications for all channels attached to the route.
    """

    if not alert.route:
        return 0

    text = format_alert_message(alert, event_type)
    sent_count = 0

    for link in routes_repo.list_route_channels(alert.route.id):
        channel = link.channel
        if not channel.enabled:
            continue

        try:
            notifier = get_notifier(channel.channel_type)
        except RuntimeError:
            logger.exception(
                "unsupported notification channel type",
                extra={
                    "extra": {
                        "alert_id": alert.id,
                        "channel_id": channel.id,
                        "channel_type": channel.channel_type,
                        "event_type": event_type,
                    }
                },
            )
            continue
        delivery = notifications_repo.get_notification(alert.id, channel.id)

        if not channel_matches_alert_severity(channel, alert):
            can_update_existing_message = (
                    event_type in EDITABLE_EVENTS
                    and delivery
                    and notifier.supports_update
            )

            if not can_update_existing_message:
                logger.info(
                    "notification skipped by channel severity filter",
                    extra={
                        "extra": {
                            "alert_id": alert.id,
                            "channel_id": channel.id,
                            "channel_type": channel.channel_type,
                            "event_type": event_type,
                            "alert_severity": alert.severity,
                            "allowed_severities": sorted(
                                get_channel_notify_on_severities(channel)
                            ),
                        }
                    },
                )
                continue

        try:
            if event_type in EDITABLE_EVENTS and delivery and notifier.supports_update:
                result = notifier.update(channel, alert, text, delivery, event_type=event_type) or {}
                notifications_repo.save_notification(
                    alert_id=alert.id,
                    channel_id=channel.id,
                    provider=result.get("provider") or channel.channel_type,
                    external_message_id=result.get("external_message_id"),
                    external_channel_id=result.get("external_channel_id"),
                    event_type=event_type,
                    provider_status=result.get("provider_status"),
                    provider_payload=result.get("provider_payload"),
                )
                alerts_repo.create_alert_event(alert.id, f"{event_type}_message_updated", f"Updated {channel.channel_type}:{channel.name}")
                logger.info("notification message updated", extra={"extra": {"alert_id": alert.id, "channel_id": channel.id, "event_type": event_type}})
                sent_count += 1
                continue

            result = notifier.send(channel, alert, text, event_type=event_type) or {}
            if result.get("skipped"):
                logger.info(
                    "notification skipped",
                    extra={
                        "extra": {
                            "alert_id": alert.id,
                            "channel_id": channel.id,
                            "event_type": event_type,
                            "provider": result.get("provider") or channel.channel_type,
                            "reason": result.get("skip_reason"),
                        }
                    },
                )
                continue
            notifications_repo.save_notification(
                alert_id=alert.id,
                channel_id=channel.id,
                provider=result.get("provider") or channel.channel_type,
                external_message_id=result.get("external_message_id"),
                external_channel_id=result.get("external_channel_id"),
                event_type=event_type,
                provider_status=result.get("provider_status"),
                provider_payload=result.get("provider_payload"),
            )
            alerts_repo.create_alert_event(alert.id, f"{event_type}_sent", f"Sent to {channel.channel_type}:{channel.name}")
            logger.info("notification sent", extra={"extra": {"alert_id": alert.id, "channel_id": channel.id, "event_type": event_type}})
            sent_count += 1
        except Exception as exc:
            notifications_repo.mark_notification_error(alert.id, channel.id, channel.channel_type, event_type, exc)
            alerts_repo.create_alert_event(alert.id, f"{event_type}_failed", f"{channel.channel_type}:{channel.name}: {exc}")
            logger.warning("notification failed", extra={"extra": {"alert_id": alert.id, "channel_id": channel.id, "event_type": event_type, "error": str(exc)}})

    if sent_count:
        alerts_repo.record_notification_time(alert, datetime.utcnow())

    return sent_count


def update_alert_messages(alert, event_type):
    """
    Update previously sent editable messages without creating new notifications.
    """

    if not alert.route:
        return 0

    text = format_alert_message(alert, event_type)
    updated_count = 0

    for link in routes_repo.list_route_channels(alert.route.id):
        channel = link.channel
        if not channel.enabled:
            continue

        try:
            notifier = get_notifier(channel.channel_type)
        except RuntimeError:
            logger.exception(
                "unsupported notification channel type",
                extra={
                    "extra": {
                        "alert_id": alert.id,
                        "channel_id": channel.id,
                        "channel_type": channel.channel_type,
                        "event_type": event_type,
                    }
                },
            )
            continue
        if not notifier.supports_update:
            continue

        delivery = notifications_repo.get_notification(alert.id, channel.id)
        if not delivery:
            continue

        try:
            result = notifier.update(channel, alert, text, delivery, event_type=event_type) or {}
            notifications_repo.save_notification(
                alert_id=alert.id,
                channel_id=channel.id,
                provider=result.get("provider") or channel.channel_type,
                external_message_id=result.get("external_message_id"),
                external_channel_id=result.get("external_channel_id"),
                event_type=event_type,
                provider_status=result.get("provider_status"),
                provider_payload=result.get("provider_payload"),
            )
            alerts_repo.create_alert_event(alert.id, f"{event_type}_message_updated", f"Updated {channel.channel_type}:{channel.name}")
            logger.info("notification message updated", extra={"extra": {"alert_id": alert.id, "channel_id": channel.id, "event_type": event_type}})
            updated_count += 1
        except Exception as exc:
            notifications_repo.mark_notification_error(alert.id, channel.id, channel.channel_type, event_type, exc)
            alerts_repo.create_alert_event(alert.id, f"{event_type}_update_failed", f"{channel.channel_type}:{channel.name}: {exc}")
            logger.warning("notification update failed", extra={"extra": {"alert_id": alert.id, "channel_id": channel.id, "event_type": event_type, "error": str(exc)}})

    return updated_count
