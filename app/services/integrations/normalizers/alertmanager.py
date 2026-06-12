from app.services.integrations.normalizers.common import first_event_link, add_event_link_label, make_dedup_key


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
