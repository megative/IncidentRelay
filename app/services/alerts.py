import logging
from datetime import datetime, timedelta

from app.settings import Config
from app.modules.db import alerts_repo, users_repo
from app.services import escalation_policies as escalation_policy_service
from app.services.oncall import get_current_oncall_user, get_next_rotation_user
from app.services.routing import build_group_key, find_route_for_alert
from app.services.silences import find_active_silence
from app.services.notification_service import (
    has_matching_notification_channel,
    notify_alert,
    update_alert_messages,
)


logger = logging.getLogger("oncall.alerts")


def upsert_alert(alert_data):
    """
    Create or update an alert from normalized alert data.
    """

    route = find_route_for_alert(alert_data)
    team = route.team if route else None
    rotation = route.rotation if route else None
    group_key = build_group_key(route, alert_data)
    status = alert_data.get("status") or "firing"

    if not route:
        logger.warning(
            "alert routing failed",
            extra={
                "extra": {
                    "source": alert_data.get("source"),
                    "dedup_key": alert_data.get("dedup_key"),
                    "team_slug": alert_data.get("team_slug"),
                    "routing_error": alert_data.get("routing_error"),
                }
            },
        )
        return None, False

    existing_alert = alerts_repo.find_existing_alert(alert_data["source"], alert_data["dedup_key"], Config.ALERT_GROUP_WINDOW_SECONDS)
    if existing_alert:
        existing_alert, previous_status = alerts_repo.update_alert_from_payload(existing_alert, alert_data, status, group_key)
        if status == "resolved" and previous_status != "resolved":
            alerts_repo.create_alert_event(existing_alert.id, "resolved", "Alert resolved by incoming payload")
            logger.info("alert resolved by incoming payload", extra={"extra": {"alert_id": existing_alert.id, "source": existing_alert.source}})
            notify_alert(existing_alert, event_type="resolved")
        else:
            alerts_repo.create_alert_event(existing_alert.id, "updated", "Alert updated from incoming payload")
            logger.info("alert updated", extra={"extra": {"alert_id": existing_alert.id, "source": existing_alert.source}})
        return existing_alert, False

    if status == "resolved":
        logger.info(
            "orphan resolved alert ignored",
            extra={
                "extra": {
                    "source": alert_data["source"],
                    "dedup_key": alert_data["dedup_key"],
                    "title": alert_data.get("title"),
                }
            },
        )
        return None, False

    policy = route.escalation_policy if route and route.escalation_policy else None
    policy_rule = None
    next_escalation_at = None

    assignee = get_current_oncall_user(rotation) if rotation else None

    if policy:
        policy_rule = escalation_policy_service.get_first_enabled_rule(policy)

        if policy_rule:
            policy_target_user = escalation_policy_service.resolve_rule_user(policy_rule)

            if policy_rule.target_type == "rotation" and policy_rule.target_rotation:
                rotation = policy_rule.target_rotation

            assignee = policy_target_user
            delay_seconds = escalation_policy_service.get_rule_delay_seconds(policy_rule)

            if delay_seconds:
                next_escalation_at = datetime.utcnow() + timedelta(seconds=delay_seconds)

    silence = find_active_silence(team.id if team else None, alert_data)
    if silence and status == "firing":
        status = "silenced"

    alert = alerts_repo.create_alert(
        team=team.id if team else None,
        route=route.id if route else None,
        rotation=rotation.id if rotation else None,
        escalation_policy=policy.id if policy else None,
        escalation_rule=policy_rule.id if policy_rule else None,
        next_escalation_at=next_escalation_at,
        assignee=assignee.id if assignee else None,
        source=alert_data["source"],
        external_id=alert_data.get("external_id"),
        dedup_key=alert_data["dedup_key"],
        group_key=group_key,
        title=alert_data["title"],
        message=alert_data.get("message"),
        severity=alert_data.get("severity"),
        labels=alert_data.get("labels"),
        payload=alert_data.get("payload"),
        status=status,
        first_seen_at=datetime.utcnow(),
        last_seen_at=datetime.utcnow(),
        silenced=bool(silence),
    )

    alerts_repo.create_alert_event(alert.id, "created", "Alert created")

    if alert_data.get("routing_error"):
        alerts_repo.create_alert_event(alert.id, "routing_error", alert_data["routing_error"])

    logger.info(
        "alert created",
        extra={
            "extra": {
                "alert_id": alert.id,
                "team": alert.team.slug if alert.team else None,
                "route_id": alert.route.id if alert.route else None,
                "routing_error": alert_data.get("routing_error"),
            }
        },
    )
    if silence:
        alerts_repo.create_alert_event(alert.id, "silenced", f"Matched silence: {silence.name}")
    if status == "firing":
        notify_alert(alert, event_type="notification")
    return alert, True


def acknowledge_alert(alert_id, user_id=None):
    """Acknowledge an alert."""

    alert = alerts_repo.acknowledge_alert(alert_id, user_id=user_id)
    attach_action_user(alert, user_id)

    alerts_repo.create_alert_event(
        alert.id,
        "acknowledged",
        "Alert acknowledged",
        user_id=user_id,
    )

    logger.info(
        "alert acknowledged",
        extra={"extra": {"alert_id": alert.id, "user_id": user_id}},
    )

    update_alert_messages(alert, event_type="acknowledged")

    return alert


def resolve_alert(alert_id, user_id=None):
    """Resolve an alert."""

    alert = alerts_repo.resolve_alert(alert_id)
    attach_action_user(alert, user_id)

    alerts_repo.create_alert_event(
        alert.id,
        "resolved",
        "Alert resolved",
        user_id=user_id,
    )

    logger.info(
        "alert resolved",
        extra={"extra": {"alert_id": alert.id, "user_id": user_id}},
    )

    update_alert_messages(alert, event_type="resolved")

    return alert


def maybe_escalate_alert(alert):
    """Escalate an alert according to route escalation mode."""
    if alert.escalation_policy_id:
        return maybe_escalate_alert_by_policy(alert)

    if not alert.team or not alert.team.escalation_enabled:
        return False

    if not has_matching_notification_channel(alert):
        logger.debug(
            "escalation skipped because no channel matches alert severity",
            extra={
                "extra": {
                    "alert_id": alert.id,
                    "severity": alert.severity,
                    "route_id": alert.route.id if alert.route else None,
                }
            },
        )
        return False

    if alert.reminder_count < alert.team.escalation_after_reminders:
        return False

    next_user = get_next_rotation_user(alert.rotation, alert.assignee)

    if not next_user or (alert.assignee and next_user.id == alert.assignee.id):
        return False

    alerts_repo.escalate_alert(alert, next_user.id)
    alerts_repo.create_alert_event(alert.id, "escalated", f"Escalated to {next_user.username}")
    notify_alert(alert, event_type="escalation")

    return True


def maybe_escalate_alert_by_policy(alert):
    """Escalate an alert according to its escalation policy."""
    if not alert.escalation_policy_id:
        return False

    now = datetime.utcnow()

    if not alert.next_escalation_at:
        return False

    if alert.next_escalation_at > now:
        return False

    if not has_matching_notification_channel(alert):
        logger.debug(
            "policy escalation skipped because no channel matches alert severity",
            extra={
                "extra": {
                    "alert_id": alert.id,
                    "severity": alert.severity,
                    "route_id": alert.route.id if alert.route else None,
                    "escalation_policy_id": alert.escalation_policy_id,
                }
            },
        )
        return False

    next_rule, repeat_count = escalation_policy_service.get_next_rule_for_alert(alert)

    if not next_rule:
        alert.next_escalation_at = None
        alert.save()

        alerts_repo.create_alert_event(
            alert.id,
            "escalation_stopped",
            "Escalation policy has no next rule",
        )

        return False

    next_user = escalation_policy_service.resolve_rule_user(next_rule)

    if next_rule.target_type == "rotation" and next_rule.target_rotation:
        alert.rotation = next_rule.target_rotation
    else:
        alert.rotation = None

    alert.assignee = next_user
    alert.escalation_rule = next_rule
    alert.escalation_level = (alert.escalation_level or 0) + 1
    alert.escalation_repeat_count = repeat_count
    alert.reminder_count = 0
    alert.last_escalated_at = now
    alert.next_escalation_at = escalation_policy_service.get_next_escalation_at(
        next_rule,
        now,
    )
    alert.save()

    target = next_user.username if next_user else "no assignee"
    alerts_repo.create_alert_event(
        alert.id,
        "escalated",
        f"Escalated by policy rule #{next_rule.position} to {target}",
    )

    notify_alert(alert, event_type="escalation")

    return True


def get_alert_reminder_interval(alert):
    """Return the reminder interval for an alert."""
    if alert.escalation_policy:
        return escalation_policy_service.get_policy_reminder_interval(alert)

    if not alert.rotation:
        return 0

    return alert.rotation.reminder_interval_seconds


def should_send_reminder(alert, now):
    """Check whether a reminder should be sent now."""
    reminder_interval = get_alert_reminder_interval(alert)

    if reminder_interval == 0:
        return False

    if not alert.last_notification_at:
        return True

    return alert.last_notification_at <= now - timedelta(seconds=reminder_interval)


def send_unacked_reminders():
    """Send reminder notifications for unacknowledged alerts.

    A reminder is counted only when at least one notification was actually sent.
    Alerts that do not match any enabled channel severity filter are skipped.
    """
    now = datetime.utcnow()
    count = 0

    for alert in alerts_repo.list_firing_alerts():
        if alert.escalation_policy_id:
            if maybe_escalate_alert(alert):
                count += 1
                continue

            if not alert.next_escalation_at:
                logger.debug(
                    "reminder skipped because escalation policy is exhausted",
                    extra={
                        "extra": {
                            "alert_id": alert.id,
                            "route_id": alert.route.id if alert.route else None,
                            "escalation_policy_id": alert.escalation_policy_id,
                            "escalation_rule_id": alert.escalation_rule_id,
                        }
                    },
                )
                continue

        interval = get_alert_reminder_interval(alert)

        if interval == 0:
            logger.debug(
                "reminder skipped because reminder interval is disabled",
                extra={
                    "extra": {
                        "alert_id": alert.id,
                        "team_id": alert.team.id if alert.team else None,
                        "rotation_id": alert.rotation.id if alert.rotation else None,
                    }
                },
            )
            continue

        if not has_matching_notification_channel(alert):
            logger.debug(
                "reminder skipped because no channel matches alert severity",
                extra={
                    "extra": {
                        "alert_id": alert.id,
                        "severity": alert.severity,
                        "route_id": alert.route.id if alert.route else None,
                    }
                },
            )
            continue

        if not should_send_reminder(alert, now):
            continue

        if not alert.escalation_policy_id and maybe_escalate_alert(alert):
            count += 1
            continue

        sent_count = notify_alert(alert, event_type="reminder")

        if not sent_count:
            logger.info(
                "reminder skipped because no notification was sent",
                extra={
                    "extra": {
                        "alert_id": alert.id,
                        "severity": alert.severity,
                        "route_id": alert.route.id if alert.route else None,
                    }
                },
            )
            continue

        alerts_repo.increment_reminder(alert, now)
        alerts_repo.create_alert_event(
            alert.id,
            "reminder_sent",
            f"Reminder count: {alert.reminder_count}",
        )
        count += 1

    return count


def attach_action_user(alert, user_id):
    """Attach the action user to the alert object for notification formatting."""

    if not user_id:
        alert._action_user = None
        return alert

    alert._action_user = users_repo.get_user_or_none(user_id)

    return alert
