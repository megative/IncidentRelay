import hashlib
import json

from urllib.parse import quote


def normalize_event_link(value):
    """Return a clean event/source link value."""
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    return value


def first_event_link(*values):
    """Return first non-empty event/source link."""
    for value in values:
        value = normalize_event_link(value)

        if value:
            return value

    return None


def add_event_link_label(labels, event_link):
    """Store external event link in alert labels."""
    event_link = normalize_event_link(event_link)

    if event_link:
        labels.setdefault("event_link", event_link)

    return labels


def build_zabbix_event_link(zabbix_url, event_id=None, trigger_id=None):
    """Build Zabbix event link when frontend URL is provided."""
    zabbix_url = normalize_event_link(zabbix_url)

    if not zabbix_url or not event_id:
        return None

    base_url = zabbix_url.rstrip("/")
    event_id = quote(str(event_id))

    if trigger_id:
        trigger_id = quote(str(trigger_id))
        return f"{base_url}/tr_events.php?triggerid={trigger_id}&eventid={event_id}"

    return (
        f"{base_url}/zabbix.php?action=problem.view"
        f"&filter_set=1&filter_eventids%5B%5D={event_id}"
    )


def make_hash(value):
    """
    Build a stable hash from a Python value.
    """

    return hashlib.sha256(repr(value).encode("utf-8")).hexdigest()


def make_dedup_key(source, external_id=None, title=None, labels=None):
    """
    Create a stable deduplication key.
    """

    return make_hash({"source": source, "external_id": external_id, "title": title, "labels": labels or {}})


def normalize_alertmanager(payload):
    """
    Normalize Prometheus Alertmanager payload.
    """

    result = []
    for item in payload.get("alerts", []):
        labels = item.get("labels", {})
        annotations = item.get("annotations", {})
        event_link = first_event_link(
            annotations.get("event_link"),
            annotations.get("event_url"),
            annotations.get("alert_url"),
            annotations.get("source_url"),
            annotations.get("dashboard_url"),
            annotations.get("panel_url"),
            annotations.get("runbook_url"),
            item.get("generatorURL"),
            item.get("dashboardURL"),
            item.get("panelURL"),
            item.get("silenceURL"),
            payload.get("externalURL"),
        )

        add_event_link_label(labels, event_link)

        if item.get("generatorURL"):
            labels.setdefault("generator_url", item.get("generatorURL"))

        if payload.get("externalURL"):
            labels.setdefault("alertmanager_url", payload.get("externalURL"))

        title = annotations.get("summary") or labels.get("alertname") or "Alertmanager alert"
        message = annotations.get("description") or annotations.get("message") or ""
        external_id = item.get("fingerprint") or labels.get("alertname")
        result.append({
            "source": "alertmanager",
            "team_slug": labels.get("team") or labels.get("oncall_team") or payload.get("team"),
            "external_id": external_id,
            "dedup_key": item.get("fingerprint") or make_dedup_key("alertmanager", external_id, title, labels),
            "title": title,
            "message": message,
            "severity": labels.get("severity"),
            "labels": labels,
            "payload": item,
            "status": item.get("status") or payload.get("status", "firing"),
        })
    return result


def first_non_empty(*values):
    """Return first non-empty string-like value."""
    for value in values:
        if value is None:
            continue

        if isinstance(value, str):
            value = value.strip()

        if value:
            return value

    return None


def normalize_zabbix_status(value):
    """Convert Zabbix event status to IncidentRelay alert status."""
    status = str(value or "").strip().lower()

    if status in {"ok", "resolved", "resolve", "recovery", "closed", "0"}:
        return "resolved"

    return "firing"


def normalize_zabbix_severity(value):
    """Map common Zabbix severities to IncidentRelay severities."""
    severity = str(value or "").strip().lower()

    mapping = {
        "disaster": "critical",
        "high": "critical",
        "average": "warning",
        "warning": "warning",
        "information": "info",
        "info": "info",
        "not classified": "info",
        "not_classified": "info",
    }

    return mapping.get(severity, severity or "info")


def normalize_zabbix_event_tag_value(value):
    """Keep raw event tag value readable for alert labels."""
    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip()
        return value or None

    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except Exception:
        return str(value)


def normalize_zabbix_tags(tags):
    """Normalize Zabbix tags into a flat labels dict."""
    result = {}

    if not tags:
        return result

    if isinstance(tags, dict):
        return dict(tags)

    if isinstance(tags, str):
        value = tags.strip()

        if not value:
            return result

        try:
            return normalize_zabbix_tags(json.loads(value))
        except Exception:
            # Fallback for comma-separated EVENT.TAGS-like strings.
            for item in value.split(","):
                item = item.strip()

                if not item:
                    continue

                if ":" in item:
                    key, val = item.split(":", 1)
                    result[key.strip()] = val.strip()
                else:
                    result[item] = ""

            return result

    if isinstance(tags, list):
        for item in tags:
            if not isinstance(item, dict):
                continue

            key = (
                item.get("tag")
                or item.get("name")
                or item.get("key")
            )

            if not key:
                continue

            result[str(key)] = item.get("value")

    return result


def normalize_zabbix(payload):
    """Normalize Zabbix webhook payload."""
    labels = dict(payload.get("labels") or {})

    event_tag_value = first_non_empty(
        payload.get("event_tag"),
        payload.get("event_tags"),
        labels.get("event_tag"),
    )

    if event_tag_value:
        labels.setdefault(
            "event_tag",
            normalize_zabbix_event_tag_value(event_tag_value),
        )

    labels.update(normalize_zabbix_tags(payload.get("tags")))
    labels.update(normalize_zabbix_tags(payload.get("tags_json")))
    labels.update(normalize_zabbix_tags(payload.get("event_tag")))
    labels.update(normalize_zabbix_tags(payload.get("event_tags")))

    host = first_non_empty(
        payload.get("host"),
        payload.get("host_name"),
        payload.get("hostname"),
        labels.get("host"),
        labels.get("host_name"),
        labels.get("hostname"),
    )

    event_name = first_non_empty(
        payload.get("event_name"),
        payload.get("problem_name"),
        payload.get("name"),
        labels.get("event_name"),
        labels.get("problem_name"),
    )

    trigger_name = first_non_empty(
        payload.get("trigger_name"),
        labels.get("trigger_name"),
        labels.get("trigger"),
    )

    title = first_non_empty(
        payload.get("title"),
        payload.get("subject"),
        event_name,
        trigger_name,
        labels.get("alertname"),
        "Zabbix alert",
    )

    message = first_non_empty(
        payload.get("message"),
        payload.get("description"),
        payload.get("opdata"),
        "",
    )

    if not message:
        message_parts = []

        if host:
            message_parts.append(f"Host: {host}")

        if payload.get("opdata"):
            message_parts.append(f"Operational data: {payload.get('opdata')}")

        if event_name and event_name != title:
            message_parts.append(f"Event: {event_name}")

        if trigger_name and trigger_name != title:
            message_parts.append(f"Trigger: {trigger_name}")

        message = "\n".join(message_parts)

    if host:
        labels.setdefault("host", host)

    if event_name:
        labels.setdefault("event_name", event_name)

    if trigger_name:
        labels.setdefault("trigger_name", trigger_name)

    external_id = first_non_empty(
        payload.get("event_id"),
        payload.get("eventid"),
        payload.get("trigger_id"),
        payload.get("triggerid"),
    )

    trigger_id = first_non_empty(
        payload.get("trigger_id"),
        payload.get("triggerid"),
    )

    raw_severity = first_non_empty(
        payload.get("severity"),
        payload.get("event_severity"),
        payload.get("trigger_severity"),
        labels.get("severity"),
    )

    if raw_severity:
        labels.setdefault("zabbix_severity", raw_severity)

    severity = normalize_zabbix_severity(raw_severity)

    status = normalize_zabbix_status(
        first_non_empty(
            payload.get("status"),
            payload.get("event_status"),
        )
    )

    event_link = first_event_link(
        payload.get("event_link"),
        payload.get("event_url"),
        payload.get("problem_url"),
        payload.get("trigger_url"),
        labels.get("event_link"),
        labels.get("event_url"),
        labels.get("problem_url"),
        labels.get("trigger_url"),
        build_zabbix_event_link(
            payload.get("zabbix_url"),
            event_id=first_non_empty(payload.get("event_id"), payload.get("eventid")),
            trigger_id=trigger_id,
        ),
    )

    add_event_link_label(labels, event_link)

    return [
        {
            "source": "zabbix",
            "team_slug": (
                payload.get("team")
                or labels.get("team")
                or labels.get("oncall_team")
            ),
            "external_id": external_id,
            "dedup_key": (
                payload.get("fingerprint")
                or make_dedup_key("zabbix", external_id, title, labels)
            ),
            "title": title,
            "message": message or "",
            "severity": severity,
            "labels": labels,
            "payload": payload,
            "status": status,
        }
    ]


def normalize_webhook(payload):
    """Normalize a generic webhook payload."""
    labels = dict(payload.get("labels") or {})

    event_link = first_event_link(
        payload.get("event_link"),
        payload.get("event_url"),
        payload.get("alert_url"),
        payload.get("source_url"),
        payload.get("dashboard_url"),
        payload.get("runbook_url"),
        labels.get("event_link"),
        labels.get("event_url"),
        labels.get("alert_url"),
        labels.get("source_url"),
        labels.get("dashboard_url"),
        labels.get("runbook_url"),
    )

    add_event_link_label(labels, event_link)

    title = payload.get("title") or "Webhook alert"

    return [
        {
            "source": "webhook",
            "team_slug": payload.get("team") or labels.get("team") or labels.get("oncall_team"),
            "external_id": payload.get("external_id"),
            "dedup_key": payload.get("fingerprint")
            or make_dedup_key("webhook", payload.get("external_id"), title, labels),
            "title": title,
            "message": payload.get("message") or "",
            "severity": payload.get("severity") or "info",
            "labels": labels,
            "payload": payload,
            "status": payload.get("status") or "firing",
        }
    ]
