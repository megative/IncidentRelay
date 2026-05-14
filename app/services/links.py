from app.settings import Config


def build_alert_web_url(alert_or_id):
    """Build a public browser URL for alert details."""
    alert_id = getattr(alert_or_id, "id", alert_or_id)

    if not alert_id:
        return ""

    base_url = (Config.PUBLIC_BASE_URL or "").rstrip("/")

    if not base_url:
        return ""

    return f"{base_url}/alerts/{alert_id}"
