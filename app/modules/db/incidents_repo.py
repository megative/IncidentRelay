from datetime import datetime, timedelta

from app.modules.db.models import (
    AlertGroup,
    IncidentPriority,
    IncidentResponder,
    IncidentStakeholder,
    ServiceOwner,
)
from app.modules.db import alerts_repo


DEFAULT_PRIORITY_SLUG = "p3"


def list_priorities(*, include_disabled=False):
    query = IncidentPriority.select().order_by(IncidentPriority.level.asc())

    if not include_disabled:
        query = query.where(IncidentPriority.enabled == True)  # noqa: E712

    return list(query)


def get_priority_by_slug(slug):
    return IncidentPriority.get_or_none(
        IncidentPriority.slug == slug,
        IncidentPriority.enabled == True,  # noqa: E712
    )


def get_default_priority():
    priority = IncidentPriority.get_or_none(
        IncidentPriority.default == True,  # noqa: E712
        IncidentPriority.enabled == True,  # noqa: E712
    )

    if priority:
        return priority

    return get_priority_by_slug(DEFAULT_PRIORITY_SLUG)


def priority_from_severity(severity):
    severity = (severity or "").lower()

    if severity in ("critical", "fatal", "disaster"):
        return get_priority_by_slug("p1") or get_default_priority()

    if severity in ("high", "error"):
        return get_priority_by_slug("p2") or get_default_priority()

    if severity in ("warning", "warn"):
        return get_priority_by_slug("p3") or get_default_priority()

    if severity in ("info", "notice"):
        return get_priority_by_slug("p4") or get_default_priority()

    return get_default_priority()


def set_incident_priority(group_id, priority_slug, *, user_id=None, manual=True):
    priority = get_priority_by_slug(priority_slug)

    if not priority:
        raise ValueError("priority must be one of enabled incident priorities")

    group = AlertGroup.get_by_id(group_id)
    old_priority = group.priority_slug

    group.priority = priority
    group.priority_slug = priority.slug
    group.priority_order = priority.level
    group.priority_set_manually = manual
    group.priority_set_by = user_id
    group.priority_set_at = datetime.utcnow()
    group.updated_at = datetime.utcnow()

    group.save(only=[
        AlertGroup.priority,
        AlertGroup.priority_slug,
        AlertGroup.priority_order,
        AlertGroup.priority_set_manually,
        AlertGroup.priority_set_by,
        AlertGroup.priority_set_at,
        AlertGroup.updated_at,
    ])

    alerts_repo.create_alert_event(
        group_id=group.id,
        event_type="priority_changed",
        message=f"Priority changed from {old_priority or '-'} to {priority.slug}",
        user_id=user_id,
    )

    return group


def create_incident_responder(group_id, data):
    expires_at = data.get("expires_at")

    if not expires_at and data.get("expires_after_minutes"):
        expires_at = datetime.utcnow() + timedelta(
            minutes=int(data["expires_after_minutes"])
        )

    return IncidentResponder.create(
        group=group_id,
        target_type=data["target_type"],
        target_user=data.get("target_user_id"),
        target_team=data.get("target_team_id"),
        target_rotation=data.get("target_rotation_id"),
        target_escalation_policy=data.get("target_escalation_policy_id"),
        requested_by=data.get("requested_by_id"),
        status=data.get("status") or "requested",
        message=data.get("message"),
        response_message=data.get("response_message"),
        notification_status=data.get("notification_status") or "pending",
        notification_error=data.get("notification_error"),
        requested_at=datetime.utcnow(),
        expires_at=expires_at,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def list_incident_responders(group_id):
    return list(
        IncidentResponder
        .select()
        .where(IncidentResponder.group == group_id)
        .order_by(
            IncidentResponder.created_at.asc(),
            IncidentResponder.id.asc(),
        )
    )


def get_incident_responder(responder_id):
    return IncidentResponder.get_or_none(IncidentResponder.id == responder_id)


def update_incident_responder_status(
    responder_id,
    status,
    *,
    user_id=None,
    response_message=None,
):
    responder = IncidentResponder.get_by_id(responder_id)

    responder.status = status
    responder.response_message = response_message
    responder.responded_at = datetime.utcnow()
    responder.updated_at = datetime.utcnow()

    if status == "accepted":
        responder.accepted_by = user_id

    if status == "declined":
        responder.declined_by = user_id

    responder.save()

    return responder


def create_incident_stakeholder(group_id, data):
    return IncidentStakeholder.create(
        group=group_id,
        user=data.get("user_id"),
        email=data.get("email"),
        display_name=data.get("display_name"),
        role=data.get("role") or "stakeholder",
        source=data.get("source") or "manual",
        notify_on_created=data.get("notify_on_created", True),
        notify_on_priority_change=data.get("notify_on_priority_change", True),
        notify_on_status_change=data.get("notify_on_status_change", True),
        notify_on_resolved=data.get("notify_on_resolved", True),
        active=data.get("active", True),
        created_by=data.get("created_by_id"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def list_incident_stakeholders(group_id, *, include_inactive=False):
    query = (
        IncidentStakeholder
        .select()
        .where(IncidentStakeholder.group == group_id)
        .order_by(
            IncidentStakeholder.created_at.asc(),
            IncidentStakeholder.id.asc(),
        )
    )

    if not include_inactive:
        query = query.where(IncidentStakeholder.active == True)  # noqa: E712

    return list(query)


def get_incident_stakeholder(stakeholder_id):
    return IncidentStakeholder.get_or_none(
        IncidentStakeholder.id == stakeholder_id
    )


def deactivate_incident_stakeholder(stakeholder_id):
    updated = (
        IncidentStakeholder
        .update(
            active=False,
            updated_at=datetime.utcnow(),
        )
        .where(
            IncidentStakeholder.id == stakeholder_id,
            IncidentStakeholder.active == True,  # noqa: E712
        )
        .execute()
    )

    return bool(updated)


def add_service_stakeholders_to_incident(group):
    if not group.service_id:
        return []

    rows = []

    owners = (
        ServiceOwner
        .select()
        .where(
            ServiceOwner.service == group.service_id,
            ServiceOwner.active == True,  # noqa: E712
            ServiceOwner.role.in_((
                "stakeholder",
                "business_owner",
                "owner",
            )),
        )
    )

    for owner in owners:
        exists = (
            IncidentStakeholder
            .select()
            .where(
                IncidentStakeholder.group == group.id,
                IncidentStakeholder.user == owner.user_id,
                IncidentStakeholder.active == True,  # noqa: E712
            )
            .exists()
        )

        if exists:
            continue

        rows.append(
            create_incident_stakeholder(
                group.id,
                {
                    "user_id": owner.user_id,
                    "role": owner.role,
                    "source": "service_owner",
                    "created_by_id": None,
                    "notify_on_created": True,
                    "notify_on_priority_change": True,
                    "notify_on_status_change": True,
                    "notify_on_resolved": True,
                },
            )
        )

    return rows
