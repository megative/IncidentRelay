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
from app.services.service_resolution import (
    get_effective_escalation_policy,
    get_effective_route_rotation,
    resolve_alert_service,
)


logger = logging.getLogger("oncall.alerts")


def _create_group_for_alert(alert_data, route, team, service, rotation, group_key, status):
    policy = get_effective_escalation_policy(route, service) if route else None

    policy_rule, rotation, assignee, next_escalation_at = (
        apply_initial_escalation_policy_assignment(policy, rotation)
    )

    return alerts_repo.create_alert_group(
        team=team.id if team else None,
        route=route.id if route else None,
        service=service.id if service else None,
        rotation=rotation.id if rotation else None,
        escalation_policy=policy.id if policy else None,
        escalation_rule=policy_rule.id if policy_rule else None,
        next_escalation_at=next_escalation_at,
        assignee=assignee.id if assignee else None,
        source=alert_data["source"],
        group_key=group_key,
        title=alert_data["title"],
        message=alert_data.get("message"),
        severity=alert_data.get("severity"),
        status=status,
        first_seen_at=datetime.utcnow(),
        last_seen_at=datetime.utcnow(),
    )


def apply_initial_escalation_policy_assignment(policy, fallback_rotation):
    """Return initial policy rule, rotation, assignee and next escalation time."""
    policy_rule = None
    rotation = fallback_rotation
    assignee = get_current_oncall_user(rotation) if rotation else None
    next_escalation_at = None

    if not policy:
        return policy_rule, rotation, assignee, next_escalation_at

    policy_rule = escalation_policy_service.get_first_enabled_rule(policy)

    if not policy_rule:
        return policy_rule, rotation, assignee, next_escalation_at

    policy_target_user = escalation_policy_service.resolve_rule_user(policy_rule)

    if policy_rule.target_type == "rotation" and policy_rule.target_rotation:
        rotation = policy_rule.target_rotation
    else:
        rotation = None

    assignee = policy_target_user

    delay_seconds = escalation_policy_service.get_rule_delay_seconds(policy_rule)

    if delay_seconds:
        next_escalation_at = datetime.utcnow() + timedelta(seconds=delay_seconds)

    return policy_rule, rotation, assignee, next_escalation_at


def _alert_group_wait_seconds():
    return int(getattr(Config, "ALERT_GROUP_WAIT_SECONDS", 30) or 0)


def _alert_group_interval_seconds():
    return int(getattr(Config, "ALERT_GROUP_INTERVAL_SECONDS", 300) or 0)


def _schedule_group_notification(group, reason="notification", now=None):
    """Schedule group notification according to group_wait/group_interval."""

    now = now or datetime.utcnow()

    if group.status != "firing":
        alerts_repo.clear_alert_group_notification(group)
        return group

    if not group.last_notification_at:
        due_at = now + timedelta(seconds=_alert_group_wait_seconds())
    else:
        next_allowed_at = (
            group.last_notification_at
            + timedelta(seconds=_alert_group_interval_seconds())
        )

        due_at = now if next_allowed_at <= now else next_allowed_at

    return alerts_repo.schedule_alert_group_notification(
        group,
        due_at=due_at,
        reason=reason,
    )


def upsert_alert(alert_data):
    """Create/update concrete alert and attach it to an alert group.

    Return:
        tuple[AlertGroup | None, bool]:
            - group object or None
            - True if a new group was created, False otherwise
    """

    route = find_route_for_alert(alert_data)

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

    team = route.team
    service = resolve_alert_service(route, alert_data)
    rotation = get_effective_route_rotation(route, service)

    status = alert_data.get("status") or "firing"

    group_key = build_group_key(
        route,
        alert_data,
        service=service,
    )

    now = datetime.utcnow()

    existing_alert = alerts_repo.find_existing_alert(
        alert_data["source"],
        alert_data["dedup_key"],
        Config.ALERT_GROUP_WINDOW_SECONDS,
    )

    existing_group = alerts_repo.find_open_alert_group(
        source=alert_data["source"],
        group_key=group_key,
        team_id=team.id if team else None,
        route_id=route.id if route else None,
        service_id=service.id if service else None,
    )

    # Existing concrete alert: this is dedup/update, not a new child alert.
    # Do not reopen acknowledged group just because the same alert was updated.
    if existing_alert:
        group = existing_alert.group or existing_group

        if not group:
            policy = get_effective_escalation_policy(route, service)
            policy_rule, rotation, assignee, next_escalation_at = (
                apply_initial_escalation_policy_assignment(policy, rotation)
            )

            group = alerts_repo.create_alert_group(
                team=team.id if team else None,
                route=route.id if route else None,
                service=service.id if service else None,
                rotation=rotation.id if rotation else None,
                escalation_policy=policy.id if policy else None,
                escalation_rule=policy_rule.id if policy_rule else None,
                next_escalation_at=next_escalation_at,
                assignee=assignee.id if assignee else None,
                source=alert_data["source"],
                group_key=group_key,
                title=alert_data["title"],
                message=alert_data.get("message"),
                severity=alert_data.get("severity"),
                status=status,
                first_seen_at=existing_alert.first_seen_at or now,
                last_seen_at=now,
                silenced=bool(existing_alert.silenced),
            )

            alerts_repo.create_alert_event(
                group_id=group.id,
                event_type="created",
                message="Alert group created for existing alert",
            )

        existing_alert, previous_status = alerts_repo.update_alert_from_payload(
            existing_alert,
            alert_data,
            status,
            group_key,
        )

        existing_alert.team = team.id if team else None
        existing_alert.route = route.id if route else None
        existing_alert.service = service.id if service else None
        existing_alert.rotation = rotation.id if rotation else None
        existing_alert.group = group.id
        existing_alert.save()

        if status == "resolved" and previous_status != "resolved":
            alerts_repo.create_alert_event(
                alert_id=existing_alert.id,
                group_id=group.id,
                event_type="resolved",
                message="Alert resolved by incoming payload",
            )
        else:
            alerts_repo.create_alert_event(
                alert_id=existing_alert.id,
                group_id=group.id,
                event_type="updated",
                message="Alert updated from incoming payload",
            )

        group = alerts_repo.recalculate_alert_group(group)

        if status == "resolved":
            if group.status == "resolved":
                alerts_repo.clear_alert_group_notification(group)

                if group.last_notification_at:
                    notify_alert(group, event_type="resolved")
            elif group.status == "firing":
                _schedule_group_notification(
                    group,
                    reason="update",
                    now=now,
                )
        else:
            if group.status == "firing":
                _schedule_group_notification(
                    group,
                    reason="update",
                    now=now,
                )

        return group, False

    # Do not create a new active alert/group from an orphan resolved payload.
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

    policy = get_effective_escalation_policy(route, service)
    policy_rule, rotation, assignee, next_escalation_at = (
        apply_initial_escalation_policy_assignment(policy, rotation)
    )

    silence = find_active_silence(team.id if team else None, alert_data)

    if silence and status == "firing":
        status = "silenced"

    group = existing_group
    created_group = False

    if not group:
        group = alerts_repo.create_alert_group(
            team=team.id if team else None,
            route=route.id if route else None,
            service=service.id if service else None,
            rotation=rotation.id if rotation else None,
            escalation_policy=policy.id if policy else None,
            escalation_rule=policy_rule.id if policy_rule else None,
            next_escalation_at=next_escalation_at,
            assignee=assignee.id if assignee else None,
            source=alert_data["source"],
            group_key=group_key,
            title=alert_data["title"],
            message=alert_data.get("message"),
            severity=alert_data.get("severity"),
            status=status,
            first_seen_at=now,
            last_seen_at=now,
            silenced=bool(silence),
        )

        created_group = True

        alerts_repo.create_alert_event(
            group_id=group.id,
            event_type="created",
            message="Alert group created",
        )

    elif group.status == "acknowledged":
        # This is a new child alert inside an existing acknowledged group.
        # A new signal must make the incident visible again.
        group.previous_status = group.status
        group.status = "firing"
        group.acknowledged_by = None
        group.acknowledged_at = None
        group.updated_at = now
        group.save()

        alerts_repo.create_alert_event(
            group_id=group.id,
            event_type="reopened",
            message="New alert received in acknowledged group",
        )

    alert = alerts_repo.create_alert(
        group=group.id,
        team=team.id if team else None,
        route=route.id if route else None,
        service=service.id if service else None,
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
        first_seen_at=now,
        last_seen_at=now,
        silenced=bool(silence),
    )

    alerts_repo.create_alert_event(
        alert_id=alert.id,
        group_id=group.id,
        event_type="created",
        message="Alert created",
    )

    if alert_data.get("routing_error"):
        alerts_repo.create_alert_event(
            alert_id=alert.id,
            group_id=group.id,
            event_type="routing_error",
            message=alert_data["routing_error"],
        )

    if silence:
        alerts_repo.create_alert_event(
            alert_id=alert.id,
            group_id=group.id,
            event_type="silenced",
            message=f"Matched silence: {silence.name}",
        )

    group = alerts_repo.recalculate_alert_group(group)

    logger.info(
        "alert added to group",
        extra={
            "extra": {
                "alert_id": alert.id,
                "alert_group_id": group.id,
                "team": group.team.slug if group.team else None,
                "route_id": group.route.id if group.route else None,
                "service_id": service.id if service else None,
                "created_group": created_group,
                "group_key": group.group_key,
            }
        },
    )

    if group.status == "firing":
        _schedule_group_notification(
            group,
            reason="notification" if created_group else "update",
            now=now,
        )
    else:
        alerts_repo.clear_alert_group_notification(group)

    return group, created_group


def acknowledge_alert(alert_id, user_id=None):
    """Acknowledge an alert group."""

    group = alerts_repo.acknowledge_alert_group(alert_id, user_id=user_id)

    alerts_repo.create_alert_event(
        group_id=group.id,
        event_type="acknowledged",
        message="Alert group acknowledged",
        user_id=user_id,
    )

    update_alert_messages(group, event_type="acknowledged")

    return group


def resolve_alert(alert_id, user_id=None):
    """Resolve an alert group."""

    group = alerts_repo.resolve_alert_group(alert_id, user_id=user_id)

    alerts_repo.create_alert_event(
        group_id=group.id,
        event_type="resolved",
        message="Alert group resolved",
        user_id=user_id,
    )

    update_alert_messages(group, event_type="resolved")

    return group


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


def process_due_alert_group_notifications(limit=100):
    """Send due alert group notifications."""

    now = datetime.utcnow()
    sent = 0
    skipped = 0
    failed = 0

    groups = alerts_repo.list_due_alert_group_notifications(
        now=now,
        limit=limit,
    )

    for group in groups:
        try:
            group = alerts_repo.recalculate_alert_group(group)

            if group.status != "firing":
                alerts_repo.clear_alert_group_notification(group)
                skipped += 1
                continue

            event_type = (
                "notification"
                if not group.last_notification_at
                else "update"
            )

            notify_alert(group, event_type=event_type)

            alerts_repo.mark_alert_group_notification_sent(group, now=now)

            alerts_repo.create_alert_event(
                group_id=group.id,
                event_type=f"{event_type}_sent",
                message="Due alert group notification sent",
            )

            sent += 1

        except Exception as exc:
            failed += 1

            logger.exception(
                "failed to send due alert group notification",
                extra={
                    "extra": {
                        "alert_group_id": getattr(group, "id", None),
                        "error": str(exc),
                    }
                },
            )

    return {
        "processed": len(groups),
        "sent": sent,
        "skipped": skipped,
        "failed": failed,
    }
