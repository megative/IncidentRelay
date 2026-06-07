from app.modules.db import alerts_repo
from app.services.notification_service import notify_alert


VALID_RESPONDER_TARGETS = {
    "user",
    "team",
    "rotation",
    "escalation_policy",
}

VALID_RESPONDER_STATUSES = {
    "requested",
    "accepted",
    "declined",
    "resolved",
}

VALID_PRIORITIES = {
    "p1",
    "p2",
    "p3",
    "p4",
    "p5",
}


def apply_maintenance_to_incoming_alert(*, team, service, alert_data, status, now):
    if status != "firing":
        return status, None, False

    window = alerts_repo.find_active_maintenance_window(
        group_id=team.group_id if team else None,
        team_id=team.id if team else None,
        service_id=service.id if service else None,
        now=now,
    )

    if not window:
        return status, None, False

    behavior = window.behavior or "suppress_notifications"

    if behavior in ("suppress", "suppress_notifications", "maintenance"):
        return "maintenance", window, True

    return status, window, False


def create_incident_responder(*, group_id, payload, user_id=None):
    target_type = payload.get("target_type")

    if target_type not in VALID_RESPONDER_TARGETS:
        raise ValueError("target_type must be one of: user, team, rotation, escalation_policy")

    data = {
        "target_type": target_type,
        "target_user_id": payload.get("target_user_id"),
        "target_team_id": payload.get("target_team_id"),
        "target_rotation_id": payload.get("target_rotation_id"),
        "target_escalation_policy_id": payload.get("target_escalation_policy_id"),
        "requested_by_id": user_id,
        "message": payload.get("message"),
        "status": "requested",
    }

    responder = alerts_repo.create_incident_responder(group_id, data)

    alerts_repo.create_alert_event(
        group_id=group_id,
        event_type="responder_added",
        message=f"Responder requested: {target_type}",
        user_id=user_id,
    )

    group = alerts_repo.get_alert_group(group_id)

    if group and group.status == "firing":
        notify_alert(group, event_type="responder_added")

    return responder


def set_incident_responder_status(*, group_id, responder_id, status, user_id=None):
    if status not in VALID_RESPONDER_STATUSES:
        raise ValueError("status must be one of: requested, accepted, declined, resolved")

    responder = alerts_repo.update_incident_responder_status(responder_id, status)

    if responder.group_id != group_id:
        raise LookupError("responder not found in this incident")

    alerts_repo.create_alert_event(
        group_id=group_id,
        event_type=f"responder_{status}",
        message=f"Responder status changed to {status}",
        user_id=user_id,
    )

    return responder


def set_incident_priority(*, group_id, priority, user_id=None):
    priority = (priority or "").lower()

    if priority not in VALID_PRIORITIES:
        raise ValueError("priority must be one of: p1, p2, p3, p4, p5")

    return alerts_repo.set_alert_group_priority(
        group_id,
        priority,
        user_id=user_id,
    )


def create_incident_stakeholder(*, group_id, payload, user_id=None):
    if not payload.get("user_id") and not payload.get("email"):
        raise ValueError("user_id or email is required")

    stakeholder = alerts_repo.create_incident_stakeholder(
        group_id,
        {
            "user_id": payload.get("user_id"),
            "email": payload.get("email"),
            "display_name": payload.get("display_name"),
            "role": payload.get("role") or "stakeholder",
            "source": "manual",
            "notify": payload.get("notify", True),
            "created_by_id": user_id,
        },
    )

    alerts_repo.create_alert_event(
        group_id=group_id,
        event_type="stakeholder_added",
        message="Stakeholder added",
        user_id=user_id,
    )

    return stakeholder
