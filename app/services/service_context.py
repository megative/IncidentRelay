from html import escape as html_escape
from typing import Any

from app.modules.db import services_repo
from app.services.matchers import match_alert


MAX_SERVICE_CONTEXT_ITEMS = 5


def _clean(value: Any) -> str:
    text = str(value or "").strip()
    return text


def _display_name(*values: Any, default: str = "-") -> str:
    for value in values:
        text = _clean(value)
        if text:
            return text
    return default


def service_display_name(alert_or_service: Any) -> str:
    """Return service display name using name first, then slug."""
    service = getattr(alert_or_service, "service", None) or alert_or_service

    if not service:
        service_id = getattr(alert_or_service, "service_id", None)
        return f"Service #{service_id}" if service_id else "-"

    return _display_name(
        getattr(service, "name", None),
        getattr(service, "slug", None),
        f"Service #{getattr(service, 'id', '-')}",
    )


def _alert_service_id(alert: Any) -> int | None:
    service_id = getattr(alert, "service_id", None)
    if service_id:
        return service_id

    service = getattr(alert, "service", None)
    return getattr(service, "id", None) if service else None


def _alert_match_data(alert: Any) -> dict:
    payload = getattr(alert, "payload", None) or {}
    labels = getattr(alert, "labels", None) or {}

    if not isinstance(payload, dict):
        payload = {}

    annotations = payload.get("annotations") or {}
    if not isinstance(annotations, dict):
        annotations = {}

    return {
        "id": getattr(alert, "id", None),
        "source": getattr(alert, "source", None),
        "title": getattr(alert, "title", None),
        "message": getattr(alert, "message", None),
        "severity": getattr(alert, "severity", None),
        "status": getattr(alert, "status", None),
        "labels": labels,
        "annotations": annotations,
        "payload": payload,
        "dedup_key": getattr(alert, "dedup_key", None),
        "group_key": getattr(alert, "group_key", None),
        "service_id": _alert_service_id(alert),
    }


def get_alert_service_links(alert: Any, limit: int = MAX_SERVICE_CONTEXT_ITEMS) -> list:
    """Return enabled service links for alert service."""
    service_id = _alert_service_id(alert)
    if not service_id:
        return []

    links = services_repo.list_service_links(service_id=service_id)
    return [
        link
        for link in links
        if getattr(link, "enabled", True) and not getattr(link, "deleted", False)
    ][:limit]


def _runbook_matches_alert(runbook: Any, alert: Any) -> bool:
    matchers = getattr(runbook, "matchers", None) or {}

    # Empty matchers mean generic service runbook.
    if not matchers:
        return True

    try:
        return bool(match_alert(_alert_match_data(alert), matchers))
    except Exception:
        return False


def get_alert_service_runbooks(alert: Any, limit: int = MAX_SERVICE_CONTEXT_ITEMS) -> list:
    """Return enabled runbooks matching this alert."""
    service_id = _alert_service_id(alert)
    if not service_id:
        return []

    runbooks = services_repo.list_service_runbooks(service_id=service_id)
    matched = [
        runbook
        for runbook in runbooks
        if getattr(runbook, "enabled", True)
        and not getattr(runbook, "deleted", False)
        and _runbook_matches_alert(runbook, alert)
    ]
    return matched[:limit]


def link_display_label(link: Any) -> str:
    """Return link label using label first, then url."""
    return _display_name(
        getattr(link, "label", None),
        getattr(link, "url", None),
        f"Link #{getattr(link, 'id', '-')}",
    )


def runbook_display_label(runbook: Any) -> str:
    """Return runbook label using title first, then url."""
    severity = _clean(getattr(runbook, "severity", None))
    title = _display_name(
        getattr(runbook, "title", None),
        getattr(runbook, "url", None),
        f"Runbook #{getattr(runbook, 'id', '-')}",
    )

    if severity:
        return f"{title} ({severity})"

    return title


def format_service_context_plain(alert: Any) -> list[str]:
    """Return plain text service links/runbooks lines."""
    links = get_alert_service_links(alert)
    runbooks = get_alert_service_runbooks(alert)

    lines: list[str] = []

    if links:
        lines.append("Links:")
        for link in links:
            label = link_display_label(link)
            url = _clean(getattr(link, "url", None))
            lines.append(f"- {label}: {url}" if url else f"- {label}")

    if runbooks:
        if lines:
            lines.append("")
        lines.append("Runbooks:")
        for runbook in runbooks:
            label = runbook_display_label(runbook)
            url = _clean(getattr(runbook, "url", None))
            lines.append(f"- {label}: {url}" if url else f"- {label}")

    return lines


def format_service_links_markdown(alert: Any) -> str:
    """Return Mattermost/Markdown service links."""
    lines = []
    for link in get_alert_service_links(alert):
        label = link_display_label(link)
        url = _clean(getattr(link, "url", None))
        lines.append(f"- [{label}]({url})" if url else f"- {label}")
    return "\n".join(lines)


def format_service_runbooks_markdown(alert: Any) -> str:
    """Return Mattermost/Markdown service runbooks."""
    lines = []
    for runbook in get_alert_service_runbooks(alert):
        label = runbook_display_label(runbook)
        url = _clean(getattr(runbook, "url", None))
        lines.append(f"- [{label}]({url})" if url else f"- {label}")
    return "\n".join(lines)


def format_service_links_html(alert: Any) -> str:
    """Return safe HTML service links."""
    lines = []
    for link in get_alert_service_links(alert):
        label = html_escape(link_display_label(link), quote=False)
        url = html_escape(_clean(getattr(link, "url", None)), quote=True)
        lines.append(f'<a href="{url}">{label}</a>' if url else label)
    return "<br>".join(lines) or "-"


def format_service_runbooks_html(alert: Any) -> str:
    """Return safe HTML service runbooks."""
    lines = []
    for runbook in get_alert_service_runbooks(alert):
        label = html_escape(runbook_display_label(runbook), quote=False)
        url = html_escape(_clean(getattr(runbook, "url", None)), quote=True)
        lines.append(f'<a href="{url}">{label}</a>' if url else label)
    return "<br>".join(lines) or "-"
