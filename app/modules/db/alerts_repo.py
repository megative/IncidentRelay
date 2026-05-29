from functools import reduce
from operator import or_
from math import ceil
from datetime import datetime

from peewee import Case, JOIN, fn

from app.modules.db.models import Alert, AlertEvent, AlertRoute, Rotation, Service, Team, User


MAX_ALERTS_PAGE_SIZE = 100

ALERT_SEVERITY_SORT = Case(
    Alert.severity,
    (
        ("critical", 4),
        ("high", 3),
        ("medium", 2),
        ("low", 1),
    ),
    0,
)

ALERT_STATUS_SORT = Case(
    Alert.status,
    (
        ("firing", 1),
        ("acknowledged", 2),
        ("silenced", 3),
        ("resolved", 4),
    ),
    9,
)

ALERT_SORT_FIELDS = {
    "id": Alert.id,
    "status": ALERT_STATUS_SORT,
    "title": Alert.title,
    "severity": ALERT_SEVERITY_SORT,
    "team": Team.slug,
    "assignee": User.username,
    "created": Alert.first_seen_at,
    "last_seen": Alert.last_seen_at,
    "activity": Alert.last_seen_at,
    "reminders": Alert.reminder_count,
}


def normalize_alert_page(page):
    """
    Return a safe page number.
    """
    try:
        page = int(page)
    except (TypeError, ValueError):
        return 1

    return max(page, 1)


def normalize_alert_page_size(page_size):
    """
    Return a safe page size.

    The upper limit protects the API from loading too many rows at once.
    """
    try:
        page_size = int(page_size)
    except (TypeError, ValueError):
        return 25

    page_size = max(page_size, 1)

    return min(page_size, MAX_ALERTS_PAGE_SIZE)


def normalize_alert_sort(sort):
    """
    Return a whitelisted alert sort field.
    """
    if sort in ALERT_SORT_FIELDS:
        return sort

    return "activity"


def normalize_alert_order(order):
    """
    Return a safe sort order.
    """
    if order == "asc":
        return "asc"

    return "desc"


def build_alerts_query(
    team_id=None,
    team_ids=None,
    status=None,
    source=None,
    severity=None,
    service_id=None,
    service_slug=None,
    service_status=None,
    service_criticality=None,
    search=None,
):
    """
    Build the base alerts query with filters.

    Search intentionally runs on backend-visible fields only, so pagination
    works on the full filtered dataset and not only on the current page.
    """
    query = (
        Alert
        .select(Alert, Team, AlertRoute, Rotation, User)
        .join(Team, JOIN.LEFT_OUTER)
        .switch(Alert)
        .join(AlertRoute, JOIN.LEFT_OUTER)
        .switch(Alert)
        .join(Rotation, JOIN.LEFT_OUTER)
        .switch(Alert)
        .join(User, JOIN.LEFT_OUTER, on=(Alert.assignee == User.id))
    )

    if team_id:
        query = query.where(Alert.team == team_id)
    elif team_ids is not None:
        if not team_ids:
            return None

        query = query.where(Alert.team.in_(team_ids))

    if status:
        query = query.where(Alert.status == status)

    if source:
        query = query.where(Alert.source == source)

    if severity:
        query = query.where(Alert.severity == severity)

    if service_id:
        query = query.where(Alert.service == service_id)

    if service_slug:
        service_ids = (
            Service
            .select(Service.id)
            .where(
                (Service.slug == service_slug)
                & (Service.deleted == False)
            )
        )
        query = query.where(Alert.service.in_(service_ids))

    if service_status:
        service_ids = (
            Service
            .select(Service.id)
            .where(
                (Service.status == service_status)
                & (Service.deleted == False)
            )
        )
        query = query.where(Alert.service.in_(service_ids))

    if service_criticality:
        service_ids = (
            Service
            .select(Service.id)
            .where(
                (Service.criticality == service_criticality)
                & (Service.deleted == False)
            )
        )
        query = query.where(Alert.service.in_(service_ids))

    if search:
        search = str(search).strip()

        if search:
            conditions = [
                Alert.title.contains(search),
                Alert.message.contains(search),
                Alert.source.contains(search),
                Alert.external_id.contains(search),
                Alert.group_key.contains(search),
                Alert.dedup_key.contains(search),
                Alert.severity.contains(search),
                Alert.status.contains(search),
                Team.slug.contains(search),
                Team.name.contains(search),
                AlertRoute.name.contains(search),
                Rotation.name.contains(search),
                User.username.contains(search),
                User.display_name.contains(search),
            ]

            if search.isdigit():
                conditions.append(Alert.id == int(search))

            query = query.where(reduce(or_, conditions))

    return query


def apply_alert_sort(query, sort, order):
    """
    Apply whitelisted sorting to alerts query.
    """
    sort = normalize_alert_sort(sort)
    order = normalize_alert_order(order)

    expression = ALERT_SORT_FIELDS[sort]
    ordered_expression = expression.asc() if order == "asc" else expression.desc()

    if sort == "id":
        return query.order_by(ordered_expression)

    return query.order_by(ordered_expression, Alert.id.desc())


def summarize_alerts(query, total_items):
    """
    Build summary counters for the current filtered selection.
    """
    summary = {
        "firing": 0,
        "acknowledged": 0,
        "resolved": 0,
        "silenced": 0,
        "reminders": 0,
        "total": total_items,
    }

    if query is None:
        return summary

    summary_query = (
        query
        .select(
            Alert.status.alias("status"),
            fn.COUNT(Alert.id).alias("count"),
            fn.COALESCE(fn.SUM(Alert.reminder_count), 0).alias("reminders"),
        )
        .group_by(Alert.status)
    )

    for row in summary_query.dicts():
        status = row.get("status") or "unknown"
        count = row.get("count") or 0

        if status in summary:
            summary[status] = count

        summary["reminders"] += row.get("reminders") or 0

    return summary


def empty_paginated_alerts(page=1, page_size=25, sort="activity", order="desc"):
    """
    Return an empty paginated response.
    """
    page = normalize_alert_page(page)
    page_size = normalize_alert_page_size(page_size)

    return {
        "items": [],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": 0,
            "total_pages": 1,
            "from": 0,
            "to": 0,
            "has_prev": False,
            "has_next": False,
        },
        "summary": summarize_alerts(None, 0),
        "sort": {
            "field": normalize_alert_sort(sort),
            "order": normalize_alert_order(order),
        },
    }


def paginate_alerts(
    team_id=None,
    team_ids=None,
    status=None,
    source=None,
    severity=None,
    service_id=None,
    service_slug=None,
    service_status=None,
    service_criticality=None,
    search=None,
    page=1,
    page_size=25,
    sort="activity",
    order="desc",
):
    """
    Return alerts with backend pagination, filtering and sorting.
    """
    page = normalize_alert_page(page)
    page_size = normalize_alert_page_size(page_size)
    sort = normalize_alert_sort(sort)
    order = normalize_alert_order(order)

    query = build_alerts_query(
        team_id=team_id,
        team_ids=team_ids,
        status=status,
        source=source,
        severity=severity,
        service_id=service_id,
        service_slug=service_slug,
        service_status=service_status,
        service_criticality=service_criticality,
        search=search,
    )

    if query is None:
        return empty_paginated_alerts(
            page=page,
            page_size=page_size,
            sort=sort,
            order=order,
        )

    total_items = query.count()
    total_pages = max(1, int(ceil(total_items / float(page_size))))

    if page > total_pages:
        page = total_pages

    sorted_query = apply_alert_sort(query, sort, order)
    items = list(sorted_query.paginate(page, page_size))

    start_index = (page - 1) * page_size
    end_index = start_index + len(items)

    return {
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "from": start_index + 1 if total_items else 0,
            "to": end_index if total_items else 0,
            "has_prev": page > 1,
            "has_next": page < total_pages,
        },
        "summary": summarize_alerts(query, total_items),
        "sort": {
            "field": sort,
            "order": order,
        },
    }


def get_alert(alert_id):
    """
    Return an alert by id.
    """
    return Alert.get_by_id(alert_id)


def find_existing_alert(source, dedup_key, window_seconds=None):
    """
    Return an existing non-resolved alert by source and dedup key.

    Resolved alerts are final occurrences. If the same fingerprint fires again
    after resolve, a new alert must be created with a new id and first_seen_at.
    """
    return (
        Alert.select()
        .where(
            (Alert.source == source)
            & (Alert.dedup_key == dedup_key)
            & (Alert.status != "resolved")
        )
        .order_by(Alert.id.desc())
        .first()
    )


def create_alert(**kwargs):
    """
    Create an alert.
    """

    return Alert.create(**kwargs)


def update_alert_from_payload(alert, alert_data, status, group_key):
    """
    Update an alert from normalized payload data.
    """
    now = datetime.utcnow()

    alert.last_seen_at = now
    previous_status = alert.status
    alert.previous_status = previous_status
    alert.last_seen_at = datetime.utcnow()
    alert.payload = alert_data.get("payload")
    alert.labels = alert_data.get("labels")
    alert.message = alert_data.get("message")
    alert.severity = alert_data.get("severity")
    alert.group_key = group_key
    if previous_status in ("acknowledged", "silenced") and status == "firing":
        alert.status = previous_status
    else:
        alert.status = status
    if status == "resolved" and not alert.resolved_at:
        alert.resolved_at = now
    alert.save()
    return alert, previous_status


def acknowledge_alert(alert_id, user_id=None):
    """
    Mark an alert as acknowledged.
    """

    alert = get_alert(alert_id)
    alert.status = "acknowledged"
    alert.acknowledged_by = user_id
    alert.acknowledged_at = datetime.utcnow()
    alert.save()
    return alert


def resolve_alert(alert_id):
    """
    Mark an alert as resolved.
    """

    alert = get_alert(alert_id)
    alert.status = "resolved"
    alert.resolved_at = datetime.utcnow()
    alert.save()
    return alert


def list_firing_alerts():
    """
    Return firing alerts for reminder evaluation.
    """

    return list(Alert.select().where(Alert.status == "firing"))


def record_notification_time(alert, now):
    """
    Update alert notification time.
    """

    alert.last_notification_at = now
    alert.save()
    return alert


def increment_reminder(alert, now):
    """
    Increment reminder count.
    """

    alert.reminder_count += 1
    alert.last_notification_at = now
    alert.save()
    return alert


def escalate_alert(alert, user_id):
    """
    Assign an alert to another user and increase escalation level.
    """

    alert.assignee = user_id
    alert.escalation_level += 1
    alert.reminder_count = 0
    alert.save()
    return alert


def create_alert_event(alert_id, event_type, message=None, user_id=None):
    """
    Create an alert event.
    """

    return AlertEvent.create(alert=alert_id, event_type=event_type, message=message, user=user_id)


def list_alert_events(alert_id):
    """
    Return alert events.
    """

    return list(
        AlertEvent.select()
        .where(AlertEvent.alert == alert_id)
        .order_by(AlertEvent.id.asc())
    )
