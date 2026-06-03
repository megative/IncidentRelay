import hashlib
import json
import logging
import secrets
from datetime import datetime, timedelta

from pywebpush import WebPushException, webpush

from app.modules.db.models import (
    Alert,
    BrowserPushActionToken,
    BrowserPushSubscription,
)
from app.db import database_proxy as db
from app.services.audit import write_audit
from app.services.links import build_alert_web_url
from app.settings import Config


logger = logging.getLogger("oncall.notifications")


def get_public_config():
    return {
        "enabled": bool(Config.BROWSER_PUSH_ENABLED),
        "public_key": Config.BROWSER_PUSH_VAPID_PUBLIC_KEY or None,
    }


def serialize_subscription(subscription):
    return {
        "id": subscription.id,
        "device_name": subscription.device_name,
        "user_agent": subscription.user_agent,
        "enabled": subscription.enabled,
        "created_at": subscription.created_at.isoformat() if subscription.created_at else None,
        "last_seen_at": subscription.last_seen_at.isoformat() if subscription.last_seen_at else None,
    }


def list_user_subscriptions(user):
    rows = (
        BrowserPushSubscription
        .select()
        .where(
            (BrowserPushSubscription.user == user.id)
            & (BrowserPushSubscription.deleted == False)
        )
        .order_by(BrowserPushSubscription.id.desc())
    )

    return [serialize_subscription(row) for row in rows]


def save_user_subscription(user, endpoint, keys, device_name=None, user_agent=None):
    if not endpoint:
        raise ValueError("endpoint is required")

    p256dh = keys.get("p256dh")
    auth = keys.get("auth")

    if not p256dh or not auth:
        raise ValueError("subscription keys p256dh/auth are required")

    subscription = BrowserPushSubscription.get_or_none(
        BrowserPushSubscription.endpoint == endpoint
    )

    now = datetime.utcnow()

    if not subscription:
        return BrowserPushSubscription.create(
            user=user.id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
            device_name=device_name,
            user_agent=user_agent,
            enabled=True,
            deleted=False,
            created_at=now,
            updated_at=now,
            last_seen_at=now,
        )

    subscription.user = user.id
    subscription.p256dh = p256dh
    subscription.auth = auth
    subscription.device_name = device_name or subscription.device_name
    subscription.user_agent = user_agent or subscription.user_agent
    subscription.enabled = True
    subscription.deleted = False
    subscription.deleted_at = None
    subscription.updated_at = now
    subscription.last_seen_at = now
    subscription.save()

    return subscription


def disable_user_subscription(user, subscription_id):
    subscription = BrowserPushSubscription.get_or_none(
        (BrowserPushSubscription.id == subscription_id)
        & (BrowserPushSubscription.user == user.id)
    )

    if not subscription:
        return None

    subscription.enabled = False
    subscription.deleted = True
    subscription.deleted_at = datetime.utcnow()
    subscription.updated_at = datetime.utcnow()
    subscription.save()

    return subscription


def _hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_action_token(user, alert, action):
    raw_token = secrets.token_urlsafe(32)
    ttl = int(getattr(Config, "BROWSER_PUSH_ACTION_TOKEN_TTL_SECONDS", 900))

    BrowserPushActionToken.create(
        user=user.id,
        alert=alert.id,
        action=action,
        token_hash=_hash_token(raw_token),
        expires_at=datetime.utcnow() + timedelta(seconds=ttl),
    )

    return raw_token


def _subscription_info(subscription):
    return {
        "endpoint": subscription.endpoint,
        "keys": {
            "p256dh": subscription.p256dh,
            "auth": subscription.auth,
        },
    }


def _webpush(subscription, payload):
    return webpush(
        subscription_info=_subscription_info(subscription),
        data=json.dumps(payload),
        vapid_private_key=Config.BROWSER_PUSH_VAPID_PRIVATE_KEY,
        vapid_claims={
            "sub": Config.BROWSER_PUSH_VAPID_SUBJECT,
        },
    )


def _active_user_subscriptions(user_id):
    return list(
        BrowserPushSubscription
        .select()
        .where(
            (BrowserPushSubscription.user == user_id)
            & (BrowserPushSubscription.enabled == True)
            & (BrowserPushSubscription.deleted == False)
        )
    )


def has_active_user_subscriptions(user_id):
    if not Config.BROWSER_PUSH_ENABLED:
        return False

    if not user_id:
        return False

    return (
        BrowserPushSubscription
        .select(BrowserPushSubscription.id)
        .where(
            (BrowserPushSubscription.user == user_id)
            & (BrowserPushSubscription.enabled == True)
            & (BrowserPushSubscription.deleted == False)
        )
        .exists()
    )


def can_send_alert_push(alert):
    return has_active_user_subscriptions(getattr(alert, "assignee_id", None))


def build_alert_push_payload(alert, user, event_type="notification"):
    action_tokens = {}

    if alert.status == "firing":
        action_tokens["ack"] = create_action_token(user, alert, "ack")
        action_tokens["resolve"] = create_action_token(user, alert, "resolve")
    elif alert.status == "acknowledged":
        action_tokens["resolve"] = create_action_token(user, alert, "resolve")

    return {
        "title": _build_alert_push_title(alert, event_type),
        "body": _build_alert_push_body(alert, event_type),
        "alert_id": alert.id,
        "alert_title": alert.title,
        "status": alert.status,
        "url": build_alert_web_url(alert) or f"/alerts/{alert.id}",
        "tag": f"incidentrelay-alert-{alert.id}",
        "require_interaction": True,
        "renotify": True,
        "silent": False,
        "vibrate": [300, 100, 300],
        "event_type": event_type,
        "action_tokens": action_tokens,
    }


def send_alert_push_to_user(user, alert, event_type="notification"):
    if not Config.BROWSER_PUSH_ENABLED:
        return 0

    subscriptions = _active_user_subscriptions(user.id)

    if not subscriptions:
        return 0

    payload = build_alert_push_payload(alert, user, event_type=event_type)
    sent = 0

    for subscription in subscriptions:
        try:
            _webpush(subscription, payload)
            subscription.last_seen_at = datetime.utcnow()
            subscription.save()
            sent += 1
        except WebPushException as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)

            if status_code in {404, 410}:
                subscription.enabled = False
                subscription.deleted = True
                subscription.deleted_at = datetime.utcnow()
                subscription.updated_at = datetime.utcnow()
                subscription.save()

            logger.warning(
                "browser push failed",
                extra={
                    "extra": {
                        "event_type": "browser_push_failed",
                        "user_id": user.id,
                        "subscription_id": subscription.id,
                        "status_code": status_code,
                        "error": str(exc),
                    }
                },
            )

    return sent


def send_test_push(user):
    payload = {
        "title": "IncidentRelay test push",
        "body": "Browser push notifications are enabled for this device.",
        "url": "/profile",
        "tag": "incidentrelay-test-push",
        "require_interaction": True,
        "renotify": True,
        "silent": False,
        "action_tokens": {},
    }

    sent = 0

    for subscription in _active_user_subscriptions(user.id):
        try:
            _webpush(subscription, payload)
            subscription.last_seen_at = datetime.utcnow()
            subscription.save()
            sent += 1
        except WebPushException as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)

            if status_code in {404, 410}:
                subscription.enabled = False
                subscription.deleted = True
                subscription.deleted_at = datetime.utcnow()
                subscription.updated_at = datetime.utcnow()
                subscription.save()

            logger.warning(
                "browser push test failed",
                extra={
                    "extra": {
                        "event_type": "browser_push_test_failed",
                        "user_id": user.id,
                        "subscription_id": subscription.id,
                        "status_code": status_code,
                        "error": str(exc),
                    }
                },
            )

    return sent


def execute_push_action(token, action):
    if action not in {"ack", "resolve"}:
        return {"ok": False, "error": "invalid_action"}

    if not token:
        return {"ok": False, "error": "missing_token"}

    token_hash = _hash_token(token)
    now = datetime.utcnow()

    record = BrowserPushActionToken.get_or_none(
        BrowserPushActionToken.token_hash == token_hash
    )

    if not record:
        return {"ok": False, "error": "invalid_token"}

    if record.used_at:
        return {"ok": False, "error": "token_already_used"}

    if record.expires_at < now:
        return {"ok": False, "error": "token_expired"}

    if record.action != action:
        return {"ok": False, "error": "action_mismatch"}

    with db.atomic():
        updated = (
            BrowserPushActionToken
            .update(used_at=now)
            .where(
                BrowserPushActionToken.id == record.id,
                BrowserPushActionToken.used_at.is_null(True),
                BrowserPushActionToken.expires_at >= now,
                BrowserPushActionToken.action == action,
            )
            .execute()
        )

        if updated != 1:
            return {"ok": False, "error": "token_already_used"}

        alert = Alert.get_or_none(Alert.id == record.alert_id)

        if not alert:
            return {"ok": False, "error": "alert_not_found"}

        result_alert = _run_alert_push_action(
            alert.id,
            user_id=record.user_id,
            action=action,
        )

        if action == "ack":
            audit_event = "alert.ack.browser_push"
        else:
            audit_event = "alert.resolve.browser_push"

        write_audit(
            audit_event,
            object_type="alert",
            object_id=result_alert.id,
            team_id=result_alert.team_id,
            user_id=record.user_id,
            data={
                "source": "browser_push",
                "action": action,
            },
        )

    return {
        "ok": True,
        "action": action,
        "alert_id": result_alert.id,
        "status": result_alert.status,
    }


def _run_alert_push_action(alert_id, user_id, action):
    """
    Run alert action from browser push.

    Imported lazily to avoid circular import:
    alerts -> notifier registry -> browser_push -> alerts.
    """
    from app.services.alerts import acknowledge_alert, resolve_alert

    if action == "ack":
        return acknowledge_alert(alert_id, user_id=user_id)

    if action == "resolve":
        return resolve_alert(alert_id, user_id=user_id)

    raise ValueError(f"unsupported browser push action: {action}")


def _build_alert_push_title(alert, event_type):
    normalized_event_type = (event_type or "").lower()
    status = (alert.status or "").lower()

    if normalized_event_type in {"resolved", "resolve"} or status == "resolved":
        return f"RESOLVED: {alert.title}"

    if normalized_event_type in {"acknowledged", "ack"} or status == "acknowledged":
        return f"ACKNOWLEDGED: {alert.title}"

    if normalized_event_type == "reminder":
        return f"REMINDER: {alert.title}"

    if normalized_event_type == "escalation":
        return f"ESCALATION: {alert.title}"

    severity = alert.severity or "unknown"
    return f"{severity.upper()}: {alert.title}"


def _build_alert_push_body(alert, event_type):
    normalized_event_type = (event_type or "").lower()

    if normalized_event_type in {"resolved", "resolve"}:
        return alert.message or alert.source or "Alert has been resolved."

    if normalized_event_type in {"acknowledged", "ack"}:
        return alert.message or alert.source or "Alert has been acknowledged."

    return alert.message or alert.source or "IncidentRelay alert"
