from functools import reduce
from operator import or_
from math import ceil
from datetime import datetime
import hashlib

from peewee import Case, JOIN, fn

from app.modules.db.models import (
    Alert,
    AlertEvent,
    AlertGroup,
    AlertGroupMerge,
    AlertRoute,
    Rotation,
    Service,
    Team,
    User,
)
from app.modules.db.query_filters import apply_field_values_filter


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

ALERT_GROUP_STATUS_SORT = Case(
    AlertGroup.status,
    (
        ("firing", 1),
        ("acknowledged", 2),
        ("silenced", 3),
        ("resolved", 4),
        ("merged", 5),
    ),
    9,
)

ALERT_GROUP_SEVERITY_SORT = Case(
    AlertGroup.severity,
    (
        ("critical", 4),
        ("high", 3),
        ("medium", 2),
        ("low", 1),
    ),
    0,
)

ALERT_GROUP_SORT_FIELDS = {
    "id": AlertGroup.id,
    "status": ALERT_GROUP_STATUS_SORT,
    "title": AlertGroup.title,
    "severity": ALERT_GROUP_SEVERITY_SORT,
    "team": Team.slug,
    "assignee": User.username,
    "created": AlertGroup.first_seen_at,
    "last_seen": AlertGroup.last_seen_at,
    "activity": AlertGroup.last_seen_at,
    "reminders": AlertGroup.reminder_count,
}


def normalize_alert_group_sort(sort):
    """Return a whitelisted alert group sort field."""

    if sort in ALERT_GROUP_SORT_FIELDS:
        return sort

    return "activity"


def build_alert_groups_query(
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
    include_merged=False,
):
    """Build the base alert groups query with filters."""

    query = (
        AlertGroup
        .select(AlertGroup, Team, AlertRoute, Rotation, User)
        .join(Team, JOIN.LEFT_OUTER)
        .switch(AlertGroup)
        .join(AlertRoute, JOIN.LEFT_OUTER)
        .switch(AlertGroup)
        .join(Rotation, JOIN.LEFT_OUTER)
        .switch(AlertGroup)
        .join(User, JOIN.LEFT_OUTER, on=(AlertGroup.assignee == User.id))
    )

    if not include_merged:
        query = query.where(AlertGroup.merged_into.is_null(True))
        query = query.where(AlertGroup.status != "merged")

    if team_id:
        query = query.where(AlertGroup.team == team_id)
    elif team_ids is not None:
        if not team_ids:
            return None

        query = query.where(AlertGroup.team.in_(team_ids))

    if status:
        query = query.where(AlertGroup.status == status)

    if source:
        query = query.where(AlertGroup.source == source)

    if severity:
        query = query.where(AlertGroup.severity == severity)

    if service_id:
        query = query.where(AlertGroup.service == service_id)

    if service_slug:
        service_ids = (
            Service
            .select(Service.id)
            .where(
                (Service.slug == service_slug)
                & (Service.deleted == False)
            )
        )
        query = query.where(AlertGroup.service.in_(service_ids))

    if service_status:
        service_ids = (
            Service
            .select(Service.id)
            .where(
                (Service.status == service_status)
                & (Service.deleted == False)
            )
        )
        query = query.where(AlertGroup.service.in_(service_ids))

    if service_criticality:
        service_ids = (
            Service
            .select(Service.id)
            .where(
                (Service.criticality == service_criticality)
                & (Service.deleted == False)
            )
        )
        query = query.where(AlertGroup.service.in_(service_ids))

    if search:
        search = str(search).strip()

        if search:
            conditions = [
                AlertGroup.title.contains(search),
                AlertGroup.message.contains(search),
                AlertGroup.source.contains(search),
                AlertGroup.group_key.contains(search),
                AlertGroup.severity.contains(search),
                AlertGroup.status.contains(search),
                Team.slug.contains(search),
                Team.name.contains(search),
                AlertRoute.name.contains(search),
                Rotation.name.contains(search),
                User.username.contains(search),
                User.display_name.contains(search),
            ]

            if search.isdigit():
                conditions.append(AlertGroup.id == int(search))

            query = query.where(reduce(or_, conditions))

    return query


def apply_alert_group_sort(query, sort, order):
    """Apply whitelisted sorting to alert groups query."""

    sort = normalize_alert_group_sort(sort)
    order = normalize_alert_order(order)

    expression = ALERT_GROUP_SORT_FIELDS[sort]
    ordered_expression = expression.asc() if order == "asc" else expression.desc()

    if sort == "id":
        return query.order_by(ordered_expression)

    return query.order_by(ordered_expression, AlertGroup.id.desc())


def summarize_alert_groups(query, total_items):
    """Build summary counters for the current filtered group selection."""

    summary = {
        "firing": 0,
        "acknowledged": 0,
        "resolved": 0,
        "silenced": 0,
        "merged": 0,
        "reminders": 0,
        "alerts": 0,
        "total": total_items,
    }

    if query is None:
        return summary

    summary_query = (
        query
        .select(
            AlertGroup.status.alias("status"),
            fn.COUNT(AlertGroup.id).alias("count"),
            fn.COALESCE(fn.SUM(AlertGroup.reminder_count), 0).alias("reminders"),
            fn.COALESCE(fn.SUM(AlertGroup.alert_count), 0).alias("alerts"),
        )
        .group_by(AlertGroup.status)
    )

    for row in summary_query.dicts():
        status = row.get("status") or "unknown"
        count = row.get("count") or 0

        if status in summary:
            summary[status] = count

        summary["reminders"] += row.get("reminders") or 0
        summary["alerts"] += row.get("alerts") or 0

    return summary


def empty_paginated_alert_groups(page=1, page_size=25, sort="activity", order="desc"):
    """Return an empty paginated alert group response."""

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
        "summary": summarize_alert_groups(None, 0),
        "sort": {
            "field": normalize_alert_group_sort(sort),
            "order": normalize_alert_order(order),
        },
    }


def paginate_alert_groups(
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
    include_merged=False,
):
    """Return alert groups with backend pagination, filtering and sorting."""

    page = normalize_alert_page(page)
    page_size = normalize_alert_page_size(page_size)
    sort = normalize_alert_group_sort(sort)
    order = normalize_alert_order(order)

    query = build_alert_groups_query(
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
        include_merged=include_merged,
    )

    if query is None:
        return empty_paginated_alert_groups(
            page=page,
            page_size=page_size,
            sort=sort,
            order=order,
        )

    total_items = query.count()
    total_pages = max(1, int(ceil(total_items / float(page_size))))

    if page > total_pages:
        page = total_pages

    sorted_query = apply_alert_group_sort(query, sort, order)
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
        "summary": summarize_alert_groups(query, total_items),
        "sort": {
            "field": sort,
            "order": order,
        },
    }


def get_alert_group(group_id):
    """Return an alert group by id."""

    return AlertGroup.get_by_id(group_id)


def hash_group_key(group_key):
    """Return stable hash for potentially long group keys."""

    value = str(group_key or "")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def find_open_alert_group(source, group_key, team_id=None, route_id=None, service_id=None):
    """Return open alert group by routing/grouping key."""

    group_key_hash = hash_group_key(group_key)

    query = AlertGroup.select().where(
        (AlertGroup.source == source)
        & (AlertGroup.group_key_hash == group_key_hash)
        & (AlertGroup.status.not_in(("resolved", "merged")))
        & (AlertGroup.merged_into.is_null(True))
    )

    if team_id:
        query = query.where(AlertGroup.team == team_id)

    if route_id:
        query = query.where(AlertGroup.route == route_id)

    if service_id:
        query = query.where(AlertGroup.service == service_id)

    return query.order_by(AlertGroup.id.desc()).first()


def create_alert_group(**kwargs):
    """Create alert group."""

    group_key = kwargs.get("group_key") or ""
    kwargs["group_key_hash"] = hash_group_key(group_key)
    return AlertGroup.create(**kwargs)


def attach_alert_to_group(alert, group):
    """Attach alert to group."""

    alert.group = group
    alert.group_key = group.group_key
    alert.save()
    return alert


def list_alerts_for_group(group_id):
    """Return concrete alerts inside group."""

    return list(
        Alert.select()
        .where(Alert.group == group_id)
        .order_by(Alert.id.asc())
    )


def _collect_group_labels(alerts):
    """Build common labels and varying values for a group."""

    if not alerts:
        return {}, {}

    all_keys = set()
    for alert in alerts:
        all_keys.update((alert.labels or {}).keys())

    common = {}
    values = {}

    for key in sorted(all_keys):
        seen = []
        for alert in alerts:
            value = (alert.labels or {}).get(key)
            if value is not None and value not in seen:
                seen.append(value)

        if len(seen) == 1:
            common[key] = seen[0]
        elif seen:
            values[key] = seen

    return common, values


def recalculate_alert_group(group):
    """Recalculate counters and aggregate fields from child alerts."""

    alerts = list_alerts_for_group(group.id)
    now = datetime.utcnow()

    alert_count = len(alerts)
    firing_count = sum(1 for item in alerts if item.status == "firing")
    acknowledged_count = sum(1 for item in alerts if item.status == "acknowledged")
    resolved_count = sum(1 for item in alerts if item.status == "resolved")
    silenced_count = sum(1 for item in alerts if item.status == "silenced")

    common_labels, label_values = _collect_group_labels(alerts)

    previous_status = group.status

    if group.status != "merged":
        if alert_count and resolved_count == alert_count:
            next_status = "resolved"
        elif group.status == "acknowledged" and firing_count:
            # Group-level ack is valid even while child alerts are firing.
            # A new child alert must explicitly reopen the group in upsert_alert().
            next_status = "acknowledged"
        elif firing_count:
            next_status = "firing"
        elif silenced_count and silenced_count == alert_count:
            next_status = "silenced"
        else:
            next_status = group.status or "firing"

        group.previous_status = previous_status
        group.status = next_status

        if next_status == "resolved" and not group.resolved_at:
            group.resolved_at = now

    group.alert_count = alert_count
    group.firing_count = firing_count
    group.acknowledged_count = acknowledged_count
    group.resolved_count = resolved_count
    group.silenced_count = silenced_count

    group.common_labels = common_labels
    group.label_values = label_values
    group.last_seen_at = max(
        [item.last_seen_at for item in alerts],
        default=group.last_seen_at,
    )
    group.updated_at = now

    if alerts:
        newest = max(
            alerts,
            key=lambda item: item.last_seen_at or item.first_seen_at,
        )
        group.title = newest.title or group.title
        group.message = newest.message or group.message
        group.severity = newest.severity or group.severity

    group.save()
    return group


def acknowledge_alert_group(group_id, user_id=None):
    """Acknowledge alert group."""

    group = AlertGroup.get_by_id(group_id)
    group.previous_status = group.status
    group.status = "acknowledged"
    group.acknowledged_by = user_id
    group.acknowledged_at = datetime.utcnow()
    group.save()
    return group


def resolve_alert_group(group_id, user_id=None):
    """Resolve alert group and all child alerts."""

    now = datetime.utcnow()
    group = AlertGroup.get_by_id(group_id)

    (
        Alert.update(status="resolved", resolved_at=now)
        .where(
            (Alert.group == group.id)
            & (Alert.status != "resolved")
        )
        .execute()
    )

    group.previous_status = group.status
    group.status = "resolved"
    group.resolved_by = user_id
    group.resolved_at = now
    group.firing_count = 0
    group.acknowledged_count = 0
    group.resolved_count = Alert.select().where(Alert.group == group.id).count()
    group.updated_at = now
    group.save()

    return group


def list_firing_alert_groups():
    """Return groups for reminder/escalation processing."""

    return list(
        AlertGroup.select()
        .where(
            (AlertGroup.status == "firing")
            & (AlertGroup.merged_into.is_null(True))
        )
    )


def record_group_notification_time(group, now):
    group.last_notification_at = now
    group.save()
    return group


def increment_group_reminder(group, now):
    group.reminder_count += 1
    group.last_notification_at = now
    group.save()
    return group


def list_group_events(group_id):
    """Return group-level and child alert events."""

    alert_ids = Alert.select(Alert.id).where(Alert.group == group_id)

    return list(
        AlertEvent.select()
        .where(
            (AlertEvent.group == group_id)
            | (AlertEvent.alert.in_(alert_ids))
        )
        .order_by(AlertEvent.id.asc())
    )


def merge_alert_groups(target_group_id, source_group_ids, user_id=None, reason=None):
    """Merge source groups into target group."""

    target = AlertGroup.get_by_id(target_group_id)
    now = datetime.utcnow()

    for source_id in source_group_ids:
        if int(source_id) == int(target_group_id):
            continue

        source = AlertGroup.get_by_id(source_id)

        (
            Alert.update(group=target.id, group_key=target.group_key)
            .where(Alert.group == source.id)
            .execute()
        )

        source.previous_status = source.status
        source.status = "merged"
        source.merged_into = target.id
        source.merged_by = user_id
        source.merged_at = now
        source.merge_reason = reason
        source.updated_at = now
        source.save()

        AlertGroupMerge.create(
            source_group=source.id,
            target_group=target.id,
            merged_by=user_id,
            reason=reason,
        )

        create_alert_event(
            group_id=source.id,
            event_type="merged",
            message=f"Merged into group #{target.id}",
            user_id=user_id,
        )

    recalculate_alert_group(target)

    create_alert_event(
        group_id=target.id,
        event_type="merge_target_updated",
        message="Alert groups merged into this group",
        user_id=user_id,
    )

    return target


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
    service_ids=None,
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

    if source:
        query = query.where(Alert.source == source)

    query = apply_field_values_filter(query, Alert.status, status)
    query = apply_field_values_filter(query, Alert.severity, severity)

    service_filter_values = service_ids if service_ids is not None else service_id
    query = apply_field_values_filter(
        query,
        Alert.service,
        service_filter_values,
        value_type=int,
    )

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
    service_ids=None,
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
        service_ids=service_ids,
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


def create_alert_event(alert_id=None, event_type=None, message=None, user_id=None, group_id=None):
    """Create alert/group event."""

    return AlertEvent.create(
        alert=alert_id,
        group=group_id,
        event_type=event_type,
        message=message,
        user=user_id,
    )


def list_alert_events(alert_id):
    """
    Return alert events.
    """

    return list(
        AlertEvent.select()
        .where(AlertEvent.alert == alert_id)
        .order_by(AlertEvent.id.asc())
    )


def schedule_alert_group_notification(group, due_at, reason="notification"):
    """Schedule a pending notification for an alert group."""

    if (
        group.notification_pending
        and group.notification_due_at
        and group.notification_due_at <= due_at
    ):
        return group

    group.notification_pending = True
    group.notification_due_at = due_at
    group.notification_reason = reason
    group.updated_at = datetime.utcnow()
    group.save()

    return group


def clear_alert_group_notification(group):
    """Clear pending group notification."""

    group.notification_pending = False
    group.notification_due_at = None
    group.notification_reason = None
    group.updated_at = datetime.utcnow()
    group.save()

    return group


def mark_alert_group_notification_sent(group, now=None):
    """Mark group notification as sent."""

    now = now or datetime.utcnow()

    group.notification_pending = False
    group.notification_due_at = None
    group.notification_reason = None
    group.last_notification_at = now
    group.updated_at = now
    group.save()

    return group


def list_due_alert_group_notifications(now=None, limit=100):
    """Return groups with due pending notifications."""

    now = now or datetime.utcnow()

    return list(
        AlertGroup
        .select()
        .where(
            (AlertGroup.notification_pending == True)
            & (AlertGroup.notification_due_at.is_null(False))
            & (AlertGroup.notification_due_at <= now)
            & (AlertGroup.merged_into.is_null(True))
            & (AlertGroup.status != "merged")
        )
        .order_by(AlertGroup.notification_due_at.asc(), AlertGroup.id.asc())
        .limit(limit)
    )
