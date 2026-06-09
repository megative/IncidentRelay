import logging
from datetime import datetime, timedelta

from app.settings import Config
from app.modules.db import alerts_repo, users_repo, incidents_repo
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
from app.services.maintenance import get_maintenance_decision


logger = logging.getLogger("oncall.alerts")


def _incident_priority_from_alert(alert_data):
    """Resolve incident priority from alert severity."""
    return incidents_repo.priority_from_severity(
        alert_data.get("severity")
    )


def _incident_priority_create_kwargs(priority):
    """Return kwargs for AlertGroup/Alert priority fields."""
    return {
        "priority": priority.id if priority else None,
        "priority_slug": priority.slug if priority else "p3",
        "priority_order": priority.level if priority else 3,
    }


def _apply_priority_to_existing_alert(alert, priority):
    """Attach resolved priority to an existing child alert."""
    if not priority:
        alert.priority = None
        alert.priority_slug = "p3"
        alert.priority_order = 3
        return alert

    alert.priority = priority.id
    alert.priority_slug = priority.slug
    alert.priority_order = priority.level

    return alert


def _maybe_apply_auto_priority_to_group(group, priority):
    """
    Update incident priority automatically.

    Manual priority must never be overwritten by incoming alert severity.
    For auto priority, only upgrade to a more severe priority.
    Example: p3 -> p1 is allowed, p1 -> p3 is not automatic.
    """
    if not group or not priority:
        return group

    if getattr(group, "priority_set_manually", False):
        return group

    current_order = group.priority_order or 999

    if priority.level >= current_order:
        return group

    group.priority = priority.id
    group.priority_slug = priority.slug
    group.priority_order = priority.level
    group.priority_set_manually = False
    group.updated_at = datetime.utcnow()

    group.save(only=[
        group.__class__.priority,
        group.__class__.priority_slug,
        group.__class__.priority_order,
        group.__class__.priority_set_manually,
        group.__class__.updated_at,
    ])

    alerts_repo.create_alert_event(
        group_id=group.id,
        event_type="priority_auto_updated",
        message=f"Priority automatically updated to {priority.slug}",
    )

    return group


def _add_service_stakeholders_for_new_group(group):
    """Auto-add service stakeholders to a newly created incident."""
    try:
        incidents_repo.add_service_stakeholders_to_incident(group)
    except Exception as exc:
        logger.exception(
            "failed to auto-add service stakeholders to incident",
            extra={
                "extra": {
                    "alert_group_id": getattr(group, "id", None),
                    "service_id": getattr(group, "service_id", None),
                    "error": str(exc),
                }
            },
        )


def _maintenance_create_kwargs(maintenance_decision):
    if not maintenance_decision or not maintenance_decision.window:
        return {}

    return {
        "maintenance_window": maintenance_decision.window,
        "maintenance_behavior": maintenance_decision.behavior,
        "maintenance_suppressed": maintenance_decision.suppress_notifications,
    }


def _apply_maintenance_to_existing_alert(alert, maintenance_decision):
    if not maintenance_decision or not maintenance_decision.window:
        return

    alert.maintenance_window = maintenance_decision.window
    alert.maintenance_behavior = maintenance_decision.behavior
    alert.maintenance_suppressed = maintenance_decision.suppress_notifications


def _maybe_apply_maintenance_to_group(group, maintenance_decision):
    if not maintenance_decision or not maintenance_decision.window:
        return

    group.maintenance_window = maintenance_decision.window
    group.maintenance_behavior = maintenance_decision.behavior
    group.maintenance_suppressed = maintenance_decision.suppress_notifications
    group.save()


def _record_maintenance_match(group, maintenance_decision, *, alert_id=None):
    """Write timeline event when an alert/incident matched maintenance."""
    if not group or not maintenance_decision or not maintenance_decision.matched:
        return

    window = maintenance_decision.window

    alerts_repo.create_alert_event(
        alert_id=alert_id,
        group_id=group.id,
        event_type="maintenance_matched",
        message=(
            f"Matched maintenance window: {window.name}"
            if window
            else "Matched maintenance window"
        ),
    )


def _create_group_for_alert(alert_data, route, team, service, rotation, group_key, status):
    policy = get_effective_escalation_policy(route, service) if route else None

    policy_rule, rotation, assignee, next_escalation_at = (
        apply_initial_escalation_policy_assignment(policy, rotation)
    )

    priority = _incident_priority_from_alert(alert_data)
    priority_kwargs = _incident_priority_create_kwargs(priority)

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
        priority_set_manually=False,
        **priority_kwargs,
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
    """
    Create/update concrete alert and attach it to an incident.

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

    priority = _incident_priority_from_alert(alert_data)
    priority_kwargs = _incident_priority_create_kwargs(priority)

    group_key = build_group_key(
        route,
        alert_data,
        service=service,
    )

    now = datetime.utcnow()

    maintenance_decision = get_maintenance_decision(
        team=team,
        route=route,
        service=service,
        status=status,
        now=now,
    )

    if maintenance_decision.incident_status:
        status = maintenance_decision.incident_status

    maintenance_kwargs = _maintenance_create_kwargs(
        maintenance_decision,
    )

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

    if maintenance_decision.suppress_incident and not existing_alert and not existing_group:
        logger.info(
            "alert suppressed by maintenance window",
            extra={
                "extra": {
                    "source": alert_data["source"],
                    "dedup_key": alert_data["dedup_key"],
                    "group_key": group_key,
                    "team_id": team.id if team else None,
                    "route_id": route.id if route else None,
                    "service_id": service.id if service else None,
                    "maintenance_window_id": maintenance_decision.window.id
                    if maintenance_decision.window
                    else None,
                    "maintenance_behavior": maintenance_decision.behavior,
                }
            },
        )
        return None, False

    # Existing concrete alert: this is dedup/update, not a new child alert.
    # Do not reopen acknowledged group just because the same alert was updated.
    if existing_alert:
        group = existing_alert.group or existing_group

        if not group:
            policy = get_effective_escalation_policy(route, service)

            policy_rule, rotation, assignee, next_escalation_at = (
                apply_initial_escalation_policy_assignment(policy, rotation)
            )

            if maintenance_decision.pause_escalation_only:
                next_escalation_at = None

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
                priority_set_manually=False,
                **priority_kwargs,
                **maintenance_kwargs,
            )

            _add_service_stakeholders_for_new_group(group)

            alerts_repo.create_alert_event(
                group_id=group.id,
                event_type="created",
                message="Incident created for existing alert",
            )

            _record_maintenance_match(
                group,
                maintenance_decision,
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

        if maintenance_decision.pause_escalation_only:
            existing_alert.next_escalation_at = None

        _apply_priority_to_existing_alert(existing_alert, priority)
        _apply_maintenance_to_existing_alert(existing_alert, maintenance_decision)

        existing_alert.save()

        _maybe_apply_auto_priority_to_group(group, priority)
        _maybe_apply_maintenance_to_group(group, maintenance_decision)

        if maintenance_decision.matched:
            _record_maintenance_match(
                group,
                maintenance_decision,
                alert_id=existing_alert.id,
            )

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

        if maintenance_decision.suppress_notifications:
            alerts_repo.clear_alert_group_notification(group)

        elif status == "resolved":
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

    if maintenance_decision.pause_escalation_only:
        next_escalation_at = None

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
            priority_set_manually=False,
            **priority_kwargs,
            **maintenance_kwargs,
        )

        created_group = True

        _add_service_stakeholders_for_new_group(group)

        alerts_repo.create_alert_event(
            group_id=group.id,
            event_type="created",
            message="Incident created",
        )

        _record_maintenance_match(
            group,
            maintenance_decision,
        )

    elif group.status == "acknowledged" and status == "firing":
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
            message="New alert received in acknowledged incident",
        )

    _maybe_apply_auto_priority_to_group(group, priority)
    _maybe_apply_maintenance_to_group(group, maintenance_decision)

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
        **priority_kwargs,
        **maintenance_kwargs,
    )

    alerts_repo.create_alert_event(
        alert_id=alert.id,
        group_id=group.id,
        event_type="created",
        message="Alert created",
    )

    if maintenance_decision.matched:
        _record_maintenance_match(
            group,
            maintenance_decision,
            alert_id=alert.id,
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
        "alert added to incident",
        extra={
            "extra": {
                "alert_id": alert.id,
                "alert_group_id": group.id,
                "incident_id": group.id,
                "team": group.team.slug if group.team else None,
                "route_id": group.route.id if group.route else None,
                "service_id": service.id if service else None,
                "created_group": created_group,
                "group_key": group.group_key,
                "priority": group.priority_slug,
                "maintenance_window_id": group.maintenance_window_id,
                "maintenance_behavior": group.maintenance_behavior,
                "maintenance_suppressed": group.maintenance_suppressed,
            }
        },
    )

    if (
        status == "firing"
        and group.status == "firing"
        and not maintenance_decision.suppress_notifications
    ):
        _schedule_group_notification(
            group,
            reason="notification" if created_group else "update",
            now=now,
        )

    elif maintenance_decision.suppress_notifications:
        alerts_repo.clear_alert_group_notification(group)

    elif group.status != "firing":
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


def maybe_escalate_alert(group):
    """Escalate an alert group according to route escalation mode."""

    if group.escalation_policy_id:
        return maybe_escalate_alert_by_policy(group)

    if not group.team or not group.team.escalation_enabled:
        return False

    if not has_matching_notification_channel(group):
        logger.debug(
            "escalation skipped because no channel matches alert group severity",
            extra={
                "extra": {
                    "alert_group_id": group.id,
                    "severity": group.severity,
                    "route_id": group.route.id if group.route else None,
                }
            },
        )
        return False

    if group.reminder_count < group.team.escalation_after_reminders:
        return False

    next_user = get_next_rotation_user(group.rotation, group.assignee)

    if not next_user or (group.assignee and next_user.id == group.assignee.id):
        return False

    now = datetime.utcnow()

    group.assignee = next_user.id
    group.escalation_level = (group.escalation_level or 0) + 1
    group.reminder_count = 0
    group.last_escalated_at = now
    group.updated_at = now
    group.save()

    alerts_repo.create_alert_event(
        group_id=group.id,
        event_type="escalated",
        message=f"Escalated to {next_user.username}",
    )

    notify_alert(group, event_type="escalation")

    return True


def maybe_escalate_alert_by_policy(group):
    """Escalate an alert group according to its escalation policy."""

    if not group.escalation_policy_id:
        return False

    now = datetime.utcnow()

    if not group.next_escalation_at:
        return False

    if group.next_escalation_at > now:
        return False

    if not has_matching_notification_channel(group):
        logger.debug(
            "policy escalation skipped because no channel matches alert group severity",
            extra={
                "extra": {
                    "alert_group_id": group.id,
                    "severity": group.severity,
                    "route_id": group.route.id if group.route else None,
                    "escalation_policy_id": group.escalation_policy_id,
                }
            },
        )
        return False

    next_rule, repeat_count = escalation_policy_service.get_next_rule_for_alert(group)

    if not next_rule:
        group.next_escalation_at = None
        group.updated_at = now
        group.save()

        alerts_repo.create_alert_event(
            group_id=group.id,
            event_type="escalation_stopped",
            message="Escalation policy has no next rule",
        )

        return False

    next_user = escalation_policy_service.resolve_rule_user(next_rule)

    if next_rule.target_type == "rotation" and next_rule.target_rotation:
        group.rotation = next_rule.target_rotation
    else:
        group.rotation = None

    group.assignee = next_user
    group.escalation_rule = next_rule
    group.escalation_level = (group.escalation_level or 0) + 1
    group.escalation_repeat_count = repeat_count
    group.reminder_count = 0
    group.last_escalated_at = now
    group.next_escalation_at = escalation_policy_service.get_next_escalation_at(
        next_rule,
        now,
    )
    group.updated_at = now
    group.save()

    target = next_user.username if next_user else "no assignee"

    alerts_repo.create_alert_event(
        group_id=group.id,
        event_type="escalated",
        message=f"Escalated by policy rule #{next_rule.position} to {target}",
    )

    notify_alert(group, event_type="escalation")

    return True


def get_alert_reminder_interval(group):
    """Return the reminder interval for an alert group."""

    if group.escalation_policy:
        return escalation_policy_service.get_policy_reminder_interval(group)

    if not group.rotation:
        return 0

    return group.rotation.reminder_interval_seconds


def should_send_reminder(group, now):
    """Check whether a reminder should be sent now."""

    reminder_interval = get_alert_reminder_interval(group)

    if reminder_interval == 0:
        return False

    if not group.last_notification_at:
        return False

    return group.last_notification_at <= now - timedelta(seconds=reminder_interval)


def send_unacked_reminders():
    """Send reminder notifications for unacknowledged alert groups.

    Escalation policy checks are intentionally evaluated before reminder gating:
    policy escalation must work even when reminder interval is disabled.
    """

    now = datetime.utcnow()
    count = 0

    for group in alerts_repo.list_firing_alert_groups():
        if group.escalation_policy_id:
            if maybe_escalate_alert(group):
                count += 1
                continue

            if not group.next_escalation_at:
                logger.debug(
                    "reminder skipped because escalation policy is exhausted",
                    extra={
                        "extra": {
                            "alert_group_id": group.id,
                            "route_id": group.route.id if group.route else None,
                            "escalation_policy_id": group.escalation_policy_id,
                            "escalation_rule_id": group.escalation_rule_id,
                        }
                    },
                )
                continue

        if group.notification_pending:
            logger.debug(
                "reminder skipped because alert group notification is pending",
                extra={
                    "extra": {
                        "alert_group_id": group.id,
                        "notification_reason": group.notification_reason,
                        "notification_due_at": (
                            group.notification_due_at.isoformat()
                            if group.notification_due_at
                            else None
                        ),
                    }
                },
            )
            continue

        if not group.last_notification_at:
            logger.debug(
                "reminder skipped because initial notification was not sent yet",
                extra={
                    "extra": {
                        "alert_group_id": group.id,
                    }
                },
            )
            continue

        interval = get_alert_reminder_interval(group)

        if interval == 0:
            logger.debug(
                "reminder skipped because reminder interval is disabled",
                extra={
                    "extra": {
                        "alert_group_id": group.id,
                        "team_id": group.team.id if group.team else None,
                        "rotation_id": group.rotation.id if group.rotation else None,
                    }
                },
            )
            continue

        if not has_matching_notification_channel(group):
            logger.debug(
                "reminder skipped because no channel matches alert group severity",
                extra={
                    "extra": {
                        "alert_group_id": group.id,
                        "severity": group.severity,
                        "route_id": group.route.id if group.route else None,
                    }
                },
            )
            continue

        if not should_send_reminder(group, now):
            continue

        if not group.escalation_policy_id and maybe_escalate_alert(group):
            count += 1
            continue

        sent_count = notify_alert(group, event_type="reminder")

        if not sent_count:
            logger.info(
                "reminder skipped because no notification was sent",
                extra={
                    "extra": {
                        "alert_group_id": group.id,
                        "severity": group.severity,
                        "route_id": group.route.id if group.route else None,
                    }
                },
            )
            continue

        alerts_repo.increment_group_reminder(group, now)

        alerts_repo.create_alert_event(
            group_id=group.id,
            event_type="reminder_sent",
            message=f"Reminder count: {group.reminder_count}",
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

            sent_count = notify_alert(group, event_type=event_type)

            if not sent_count:
                alerts_repo.clear_alert_group_notification(group)

                alerts_repo.create_alert_event(
                    group_id=group.id,
                    event_type=f"{event_type}_skipped",
                    message="Due alert group notification skipped: no delivery target",
                )

                skipped += 1
                continue

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
