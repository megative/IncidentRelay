from app.services.integrations.normalizers.common import first_event_link, add_event_link_label, make_dedup_key


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
