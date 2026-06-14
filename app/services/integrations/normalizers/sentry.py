from app.services.integrations.normalizers.common import first_non_empty, first_event_link, add_event_link_label, \
    make_dedup_key


def normalize_sentry(payload, headers=None):
    """Normalize Sentry Integration Platform webhooks."""
    headers = headers or {}
    data = payload.get("data") or {}
    action = str(payload.get("action") or "").lower()

    resource = (
        headers.get("Sentry-Hook-Resource")
        or headers.get("sentry-hook-resource")
        or data.get("resource")
        or "sentry"
    )
    resource = str(resource or "").lower()

    issue = data.get("issue") or data.get("group") or {}
    event = data.get("event") or {}
    metric_alert = data.get("metric_alert") or {}
    event_alert = data.get("event_alert") or {}

    alert_obj = metric_alert or event_alert or data.get("alert") or {}

    project = (
        data.get("project")
        or issue.get("project")
        or event.get("project")
        or alert_obj.get("project")
        or {}
    )
    project_slug, project_name = normalize_sentry_named_object(project)

    organization = (
        data.get("organization")
        or payload.get("organization")
        or (payload.get("installation") or {}).get("organization")
        or {}
    )
    organization_slug, organization_name = normalize_sentry_named_object(organization)

    issue_metadata = issue.get("metadata") or {}

    issue_id = first_non_empty(
        issue.get("id"),
        issue.get("issue_id"),
        data.get("issue_id"),
        event.get("groupID"),
        event.get("group_id"),
    )
    issue_short_id = first_non_empty(
        issue.get("shortId"),
        issue.get("short_id"),
        data.get("issue_short_id"),
    )
    event_id = first_non_empty(
        event.get("event_id"),
        event.get("id"),
        data.get("event_id"),
    )

    alert_id = first_non_empty(
        metric_alert.get("id"),
        event_alert.get("id"),
        alert_obj.get("id"),
        data.get("alert_id"),
    )

    is_metric_alert = resource == "metric_alert" or bool(metric_alert)

    if is_metric_alert:
        title = first_non_empty(
            metric_alert.get("title"),
            metric_alert.get("name"),
            data.get("title"),
            "Sentry metric alert",
        )

        message = first_non_empty(
            data.get("message"),
            metric_alert.get("description"),
            metric_alert.get("name"),
            "",
        )
    else:
        title = first_non_empty(
            issue.get("title"),
            event.get("title"),
            event.get("message"),
            data.get("title"),
            event_alert.get("title"),
            event_alert.get("name"),
            "Sentry alert",
        )

        message = first_non_empty(
            data.get("message"),
            event.get("message"),
            issue_metadata.get("value"),
            issue.get("culprit"),
            event.get("culprit"),
            "",
        )

    raw_level = first_non_empty(
        metric_alert.get("status"),
        metric_alert.get("level"),
        event.get("level"),
        issue.get("level"),
        data.get("level"),
        action,
        "error",
    )

    severity = normalize_sentry_severity(raw_level, action)
    status = normalize_sentry_status(resource, action, issue, metric_alert)

    sentry_url = first_event_link(
        issue.get("permalink"),
        issue.get("web_url"),
        event.get("web_url"),
        event.get("url"),
        data.get("web_url"),
        data.get("url"),
        metric_alert.get("web_url"),
        event_alert.get("web_url"),
    )

    labels = {
        "alertname": normalize_sentry_alertname(resource, metric_alert),
        "severity": severity,
        "sentry_resource": resource,
        "sentry_action": action,
        "organization_slug": organization_slug,
        "organization_name": organization_name,
        "project_slug": project_slug,
        "project_name": project_name,
        "issue_id": str(issue_id) if issue_id else None,
        "issue_short_id": issue_short_id,
        "event_id": event_id,
        "sentry_alert_id": str(alert_id) if alert_id else None,
        "sentry_alert_name": first_non_empty(
            metric_alert.get("name"),
            metric_alert.get("title"),
            event_alert.get("name"),
            event_alert.get("title"),
        ),
        "level": raw_level,
        "environment": first_non_empty(
            event.get("environment"),
            issue.get("environment"),
            data.get("environment"),
        ),
        "culprit": first_non_empty(issue.get("culprit"), event.get("culprit")),
        "sentry_url": sentry_url,
    }

    labels = {
        key: value
        for key, value in labels.items()
        if value not in (None, "")
    }

    add_event_link_label(labels, sentry_url)

    external_id = first_non_empty(
        issue_id,
        alert_id,
        event_id,
        title,
    )

    if issue_id:
        dedup_key = "sentry:issue:" + str(issue_id)
    elif resource == "metric_alert" and alert_id:
        dedup_key = "sentry:metric:" + str(alert_id)
    elif alert_id:
        dedup_key = "sentry:alert:" + str(alert_id)
    else:
        dedup_key = make_dedup_key("sentry", external_id, title, labels)

    return [
        {
            "source": "sentry",
            "team_slug": labels.get("team") or labels.get("oncall_team"),
            "external_id": str(external_id) if external_id else None,
            "dedup_key": dedup_key,
            "title": title,
            "message": message or "",
            "severity": severity,
            "labels": labels,
            "payload": payload,
            "status": status,
        }
    ]


def normalize_sentry_named_object(value):
    if isinstance(value, str):
        return value, value

    if not isinstance(value, dict):
        return None, None

    slug = first_non_empty(value.get("slug"), value.get("name"))
    name = first_non_empty(value.get("name"), slug)

    return slug, name


def normalize_sentry_alertname(resource, metric_alert=None):
    if resource == "metric_alert" or metric_alert:
        return "SentryMetricAlert"

    if resource == "event_alert":
        return "SentryIssueAlert"

    if resource == "issue":
        return "SentryIssue"

    return "SentryAlert"


def normalize_sentry_severity(level, action=None):
    value = str(level or action or "").strip().lower()

    if value in {"fatal", "critical"}:
        return "critical"

    if value in {"error"}:
        return "critical"

    if value in {"warning", "warn"}:
        return "warning"

    if value in {"info", "debug", "resolved", "ok"}:
        return "info"

    return "warning"


def normalize_sentry_status(resource, action, issue=None, metric_alert=None):
    issue = issue or {}
    metric_alert = metric_alert or {}

    action = str(action or "").strip().lower()
    resource = str(resource or "").strip().lower()

    if resource == "metric_alert" and action in {"resolved", "ok"}:
        return "resolved"

    if resource == "issue" and action in {"resolved", "ignored", "archived"}:
        return "resolved"

    if action in {"resolved", "ignored", "archived", "closed", "ok"}:
        return "resolved"

    issue_status = str(issue.get("status") or "").strip().lower()
    if issue_status in {"resolved", "ignored", "closed"}:
        return "resolved"

    metric_status = str(metric_alert.get("status") or "").strip().lower()
    if metric_status in {"resolved", "ok", "closed"}:
        return "resolved"

    return "firing"
