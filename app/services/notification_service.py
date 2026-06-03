import logging
from datetime import datetime

from app.modules.db import alerts_repo, notifications_repo, routes_repo
from app.notifiers.registry import get_notifier
from app.services.links import build_alert_web_url
from app.services.severity import normalize_severity, normalize_severity_list
from app.services.service_context import format_service_context_plain, service_display_name
from app.notifiers.browser_push import service as browser_push
from app.services import notification_rules

EDITABLE_EVENTS = {"acknowledged", "resolved"}

logger = logging.getLogger("oncall.notifications")


def alert_service_label(alert):
    """Return a human-readable affected service label."""
    service = getattr(alert, "service", None)

    if service:
        parts = [
            getattr(service, "name", None)
            or getattr(service, "slug", None)
            or f"Service #{getattr(service, 'id', '-')}",
        ]

        criticality = getattr(service, "criticality", None)
        status = getattr(service, "status", None)

        if criticality:
            parts.append(criticality)

        if status:
            parts.append(status)

        return " / ".join(str(part) for part in parts if part)

    service_id = getattr(alert, "service_id", None)
    if service_id:
        return f"Service #{service_id}"

    return "-"


def _team_display_name(alert):
    """Return team display name using name first, then slug."""
    team = getattr(alert, "team", None)
    if not team:
        return "unknown"

    return team.name or team.slug or "unknown"


def format_alert_message(alert, event_type="notification"):
    """Format a plain text alert notification."""
    assignee = (
        alert.assignee.display_name or alert.assignee.username
        if alert.assignee
        else "unknown"
    )
    team = _team_display_name(alert)
    service = service_display_name(alert)
    alert_url = build_alert_web_url(alert)

    lines = [
        f"{event_type.upper()}: {alert.title}",
        f"Team: {team}",
        f"Service: {service}",
        f"Status: {alert.status}",
        f"Severity: {alert.severity or '-'}",
        f"Assignee: {assignee}",
        f"Source: {alert.source}",
        f"Message: {alert.message or '-'}",
    ]

    if alert_url:
        lines.append(f"Alert URL: {alert_url}")

    service_context = format_service_context_plain(alert)
    if service_context:
        lines.append("")
        lines.extend(service_context)

    return "\n".join(lines)


def notification_log_extra(channel, alert, event_type, result=None, error=None, **extra_fields):
    """Build a consistent structured log payload for notification events."""
    result = result or {}
    data = {
        "alert_id": getattr(alert, "id", None),
        "channel_id": getattr(channel, "id", None),
        "channel_name": getattr(channel, "name", None),
        "channel_type": getattr(channel, "channel_type", None),
        "event_type": event_type,
        "provider": result.get("provider") or getattr(channel, "channel_type", None),
    }

    external_message_id = result.get("external_message_id")
    if external_message_id:
        data["external_message_id"] = external_message_id

    external_channel_id = result.get("external_channel_id")
    if external_channel_id:
        data["external_channel_id"] = external_channel_id

    provider_status = result.get("provider_status")
    if provider_status:
        data["provider_status"] = provider_status

    if error is not None:
        data["error"] = str(error)

    data.update(extra_fields)
    return {"extra": data}


def browser_push_log_extra(alert, event_type, sent=None, error=None, reason=None):
    data = {
        "alert_id": getattr(alert, "id", None),
        "event_type": event_type,
        "provider": "browser_push",
        "assignee_id": getattr(alert, "assignee_id", None),
    }

    if sent is not None:
        data["sent"] = sent

    if error is not None:
        data["error"] = str(error)

    if reason:
        data["reason"] = reason

    return {"extra": data}


def send_profile_browser_push(alert, event_type="notification"):
    """Send built-in browser push to alert assignee profile devices."""

    assignee = getattr(alert, "assignee", None)

    if not assignee:
        logger.info(
            "browser push skipped",
            extra=browser_push_log_extra(
                alert,
                event_type,
                reason="no_assignee",
            ),
        )
        return 0

    try:
        sent = browser_push.send_alert_push_to_user(
            assignee,
            alert,
            event_type=event_type,
        )
    except Exception as exc:
        alerts_repo.create_alert_event(
            alert.id,
            f"{event_type}_browser_push_failed",
            f"browser_push: {exc}",
        )
        logger.warning(
            "browser push failed",
            extra=browser_push_log_extra(
                alert,
                event_type,
                error=exc,
            ),
        )
        return 0

    if not sent:
        logger.info(
            "browser push skipped",
            extra=browser_push_log_extra(
                alert,
                event_type,
                sent=0,
                reason="no_active_push_subscriptions",
            ),
        )
        return 0

    alerts_repo.create_alert_event(
        alert.id,
        f"{event_type}_browser_push_sent",
        f"Sent browser push to {sent} device(s)",
    )

    logger.info(
        "browser push sent",
        extra=browser_push_log_extra(
            alert,
            event_type,
            sent=sent,
        ),
    )

    # Return logical delivery count, not device count.
    return 1


def get_channel_notify_on_severities(channel):
    """Return normalized channel-level severity filter.

    Empty list means that the channel accepts all severities.
    """
    config = channel.config or {}
    raw_severities = config.get("notify_on_severities")

    try:
        return set(normalize_severity_list(raw_severities))
    except ValueError as exc:
        logger.warning(
            "invalid channel severity filter, ignoring it",
            extra={
                "extra": {
                    "channel_id": channel.id,
                    "channel_name": getattr(channel, "name", None),
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
    """Return True if the alert has at least one deliverable notification target.

    Browser push is profile-based, not route-channel-based.
    If the assignee has active browser push subscriptions, reminders/escalations
    can still be delivered even when the route has no regular channels.
    """
    if alert.route:
        for link in routes_repo.list_route_channels(alert.route.id):
            channel = link.channel

            if not channel.enabled:
                continue

            if channel_matches_alert_severity(channel, alert):
                return True

    return notification_rules.has_deliverable_user_notification(alert)


def notify_alert(alert, event_type="notification"):
    """Send or update alert notifications for all channels attached to the route."""
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
        except RuntimeError as exc:
            logger.exception(
                "unsupported notification channel type",
                extra=notification_log_extra(channel, alert, event_type, error=exc),
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
                    extra=notification_log_extra(
                        channel,
                        alert,
                        event_type,
                        alert_severity=alert.severity,
                        allowed_severities=sorted(get_channel_notify_on_severities(channel)),
                    ),
                )
                continue

        try:
            if event_type in EDITABLE_EVENTS and delivery and notifier.supports_update:
                result = notifier.update(
                    channel,
                    alert,
                    text,
                    delivery,
                    event_type=event_type,
                ) or {}
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
                alerts_repo.create_alert_event(
                    alert.id,
                    f"{event_type}_message_updated",
                    f"Updated {channel.channel_type}:{channel.name}",
                )
                logger.info(
                    "notification message updated",
                    extra=notification_log_extra(channel, alert, event_type, result=result),
                )
                sent_count += 1
                continue

            result = notifier.send(channel, alert, text, event_type=event_type) or {}

            if result.get("skipped"):
                logger.info(
                    "notification skipped",
                    extra=notification_log_extra(
                        channel,
                        alert,
                        event_type,
                        result=result,
                        reason=result.get("skip_reason"),
                    ),
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
            alerts_repo.create_alert_event(
                alert.id,
                f"{event_type}_sent",
                f"Sent to {channel.channel_type}:{channel.name}",
            )
            logger.info(
                "notification sent",
                extra=notification_log_extra(channel, alert, event_type, result=result),
            )
            sent_count += 1
        except Exception as exc:
            notifications_repo.mark_notification_error(
                alert.id,
                channel.id,
                channel.channel_type,
                event_type,
                exc,
            )
            alerts_repo.create_alert_event(
                alert.id,
                f"{event_type}_failed",
                f"{channel.channel_type}:{channel.name}: {exc}",
            )
            logger.warning(
                "notification failed",
                extra=notification_log_extra(channel, alert, event_type, error=exc),
            )

    sent_count += notification_rules.enqueue_user_notifications(
        alert,
        event_type=event_type,
    )

    if sent_count:
        alerts_repo.record_notification_time(alert, datetime.utcnow())

    return sent_count


def update_alert_messages(alert, event_type):
    """Update previously sent editable messages without creating new notifications."""
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
        except RuntimeError as exc:
            logger.exception(
                "unsupported notification channel type",
                extra=notification_log_extra(channel, alert, event_type, error=exc),
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
            alerts_repo.create_alert_event(
                alert.id,
                f"{event_type}_message_updated",
                f"Updated {channel.channel_type}:{channel.name}",
            )
            logger.info(
                "notification message updated",
                extra=notification_log_extra(channel, alert, event_type, result=result),
            )
            updated_count += 1
        except Exception as exc:
            notifications_repo.mark_notification_error(
                alert.id,
                channel.id,
                channel.channel_type,
                event_type,
                exc,
            )
            alerts_repo.create_alert_event(
                alert.id,
                f"{event_type}_update_failed",
                f"{channel.channel_type}:{channel.name}: {exc}",
            )
            logger.warning(
                "notification update failed",
                extra=notification_log_extra(channel, alert, event_type, error=exc),
            )

    return updated_count
