from app.modules.db import alerts_repo
from app.modules.db import incidents_repo


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
    "expired",
    "resolved",
}

VALID_STAKEHOLDER_ROLES = {
    "stakeholder",
    "business_owner",
    "executive",
    "support",
    "customer_success",
    "custom",
}


def set_incident_priority(*, group_id, priority, user_id=None):
    if not priority:
        raise ValueError("priority is required")

    group = alerts_repo.get_alert_group(group_id)

    if not group:
        raise LookupError("incident not found")

    return incidents_repo.set_incident_priority(
        group.id,
        priority,
        user_id=user_id,
        manual=True,
    )


def create_incident_responder(*, group_id, payload, user_id=None):
    group = alerts_repo.get_alert_group(group_id)

    if not group:
        raise LookupError("incident not found")

    target_type = payload.get("target_type")

    if target_type not in VALID_RESPONDER_TARGETS:
        raise ValueError(
            "target_type must be one of: user, team, rotation, escalation_policy"
        )

    target_fields = {
        "user": "target_user_id",
        "team": "target_team_id",
        "rotation": "target_rotation_id",
        "escalation_policy": "target_escalation_policy_id",
    }

    required_field = target_fields[target_type]

    if not payload.get(required_field):
        raise ValueError(f"{required_field} is required for {target_type} responder")

    responder = incidents_repo.create_incident_responder(
        group.id,
        {
            "target_type": target_type,
            "target_user_id": payload.get("target_user_id"),
            "target_team_id": payload.get("target_team_id"),
            "target_rotation_id": payload.get("target_rotation_id"),
            "target_escalation_policy_id": payload.get("target_escalation_policy_id"),
            "requested_by_id": user_id,
            "message": payload.get("message"),
            "expires_after_minutes": payload.get("expires_after_minutes"),
            "status": "requested",
        },
    )

    alerts_repo.create_alert_event(
        group_id=group.id,
        event_type="responder_requested",
        message=payload.get("message") or f"Responder requested: {target_type}",
        user_id=user_id,
    )

    return responder


def set_incident_responder_status(
    *,
    group_id,
    responder_id,
    status,
    response_message=None,
    user_id=None,
):
    group = alerts_repo.get_alert_group(group_id)

    if not group:
        raise LookupError("incident not found")

    if status not in VALID_RESPONDER_STATUSES:
        raise ValueError(
            "status must be one of: requested, accepted, declined, expired, resolved"
        )

    responder = incidents_repo.get_incident_responder(responder_id)

    if not responder or responder.group_id != group.id:
        raise LookupError("responder not found in this incident")

    responder = incidents_repo.update_incident_responder_status(
        responder.id,
        status,
        user_id=user_id,
        response_message=response_message,
    )

    alerts_repo.create_alert_event(
        group_id=group.id,
        event_type=f"responder_{status}",
        message=response_message or f"Responder status changed to {status}",
        user_id=user_id,
    )

    return responder


def create_incident_stakeholder(*, group_id, payload, user_id=None):
    group = alerts_repo.get_alert_group(group_id)

    if not group:
        raise LookupError("incident not found")

    if not payload.get("user_id") and not payload.get("email"):
        raise ValueError("user_id or email is required")

    role = payload.get("role") or "stakeholder"

    if role not in VALID_STAKEHOLDER_ROLES:
        raise ValueError(
            "role must be one of: stakeholder, business_owner, executive, support, customer_success, custom"
        )

    stakeholder = incidents_repo.create_incident_stakeholder(
        group.id,
        {
            "user_id": payload.get("user_id"),
            "email": payload.get("email"),
            "display_name": payload.get("display_name"),
            "role": role,
            "source": "manual",
            "notify_on_created": payload.get("notify_on_created", True),
            "notify_on_priority_change": payload.get("notify_on_priority_change", True),
            "notify_on_status_change": payload.get("notify_on_status_change", True),
            "notify_on_resolved": payload.get("notify_on_resolved", True),
            "created_by_id": user_id,
        },
    )

    alerts_repo.create_alert_event(
        group_id=group.id,
        event_type="stakeholder_added",
        message="Stakeholder added",
        user_id=user_id,
    )

    return stakeholder


def remove_incident_stakeholder(*, group_id, stakeholder_id, user_id=None):
    group = alerts_repo.get_alert_group(group_id)

    if not group:
        raise LookupError("incident not found")

    stakeholder = incidents_repo.get_incident_stakeholder(stakeholder_id)

    if not stakeholder or stakeholder.group_id != group.id or not stakeholder.active:
        raise LookupError("stakeholder not found in this incident")

    incidents_repo.deactivate_incident_stakeholder(stakeholder.id)

    alerts_repo.create_alert_event(
        group_id=group.id,
        event_type="stakeholder_removed",
        message="Stakeholder removed",
        user_id=user_id,
    )

    return stakeholder
