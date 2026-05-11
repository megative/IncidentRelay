import logging

from flask import Blueprint, jsonify, request

from app.api.schemas.integrations import AlertmanagerWebhookSchema, GenericWebhookSchema, ZabbixWebhookSchema
from app.settings import Config
from app.modules.db import channels_repo, users_repo, notifications_repo, alerts_repo
from app.services.alerts import acknowledge_alert, resolve_alert, upsert_alert
from app.services.auth import require_alert_token
from app.services.normalizers import normalize_alertmanager, normalize_webhook, normalize_zabbix
from app.services.validation import validate_body
from app.notifiers.voice.loader import create_voice_provider, resolve_env_values


integrations_bp = Blueprint("integrations_api", __name__)


@integrations_bp.route("/alertmanager", methods=["POST"])
@require_alert_token()
def alertmanager_webhook():
    """
    Receive alerts from Prometheus Alertmanager.
    """

    payload, error = validate_body(AlertmanagerWebhookSchema)
    if error:
        return error
    return process_incoming_alerts(normalize_alertmanager(payload.model_dump()))


@integrations_bp.route("/zabbix", methods=["POST"])
@require_alert_token()
def zabbix_webhook():
    """
    Receive alerts from Zabbix.
    """

    payload, error = validate_body(ZabbixWebhookSchema)
    if error:
        return error
    return process_incoming_alerts(normalize_zabbix(payload.model_dump()))


@integrations_bp.route("/webhook", methods=["POST"])
@require_alert_token()
def generic_webhook():
    """
    Receive alerts from a generic webhook.
    """

    payload, error = validate_body(GenericWebhookSchema)
    if error:
        return error
    return process_incoming_alerts(normalize_webhook(payload.model_dump()))


def process_incoming_alerts(normalized_alerts):
    """
    Store normalized alerts and return created or updated records.
    """

    result = []

    intake_route = getattr(request, "current_intake_route", None)

    for alert_data in normalized_alerts:
        if intake_route:
            # The route intake token is the routing boundary. Alerts submitted
            # with this token are forced to this route, which already defines
            # team, rotation and notification channels.
            alert_data["forced_route_id"] = intake_route.id
            alert_data["forced_team_id"] = intake_route.team.id
            alert_data["team_slug"] = intake_route.team.slug

        alert, created = upsert_alert(alert_data)
        if alert is None:
            return jsonify({
                "status": "ignored",
                "reason": "orphan_resolved",
            }), 202
        result.append({
            "id": alert.id,
            "team_id": alert.team.id if alert.team else None,
            "team_slug": alert.team.slug if alert.team else None,
            "route_id": alert.route.id if alert.route else None,
            "rotation_id": alert.rotation.id if alert.rotation else None,
            "routing_error": alert_data.get("routing_error"),
            "created": created,
            "status": alert.status,
            "assignee": alert.assignee.username if alert.assignee else None,
        })

    logging.getLogger("oncall.alerts").info(
        "incoming alerts processed",
        extra={
            "extra": {
                "event_type": "alert_intake",
                "source": normalized_alerts[0]["source"] if normalized_alerts else None,
                "alerts_count": len(normalized_alerts),
                "route_id": intake_route.id if intake_route else None,
                "team_id": intake_route.team.id if intake_route else None,
                "results": result,
            }
        },
    )

    return jsonify(result)


@integrations_bp.route("/mattermost/actions", methods=["POST"])
def mattermost_action():
    """
    Handle Mattermost interactive message button callbacks.
    """

    payload = request.json or {}
    context = payload.get("context") or {}
    alert_id = context.get("alert_id")
    channel_id = context.get("channel_id")
    action = context.get("action")
    secret = context.get("secret")

    if not alert_id or not channel_id or action not in {"acknowledge", "resolve"}:
        return jsonify({"ephemeral_text": "Invalid action payload"}), 400

    channel = channels_repo.get_channel(int(channel_id))
    config = channel.config or {}
    expected_secret = config.get("callback_secret") or Config.MATTERMOST_ACTION_SECRET

    if secret != expected_secret:
        return jsonify({"ephemeral_text": "Action rejected"}), 403

    mattermost_user_id = payload.get("user_id")
    user = users_repo.get_user_by_mattermost_id(mattermost_user_id)
    user_id = user.id if user else None

    if action == "acknowledge":
        alert = acknowledge_alert(int(alert_id), user_id=user_id)
        return jsonify({
            "ephemeral_text": f"Alert #{alert.id} acknowledged",
            "skip_slack_parsing": True,
        })

    alert = resolve_alert(int(alert_id), user_id=user_id)
    return jsonify({
        "ephemeral_text": f"Alert #{alert.id} resolved",
        "skip_slack_parsing": True,
    })


@integrations_bp.route("/voice/callback/<int:channel_id>/<secret>", methods=["POST"])
def voice_callback(channel_id, secret):
    """Handle voice provider callbacks.

    Supported normalized events:
    - status changes;
    - DTMF button presses;
    - provider errors.
    """

    channel = channels_repo.get_channel(channel_id)

    if channel.channel_type != "voice_call":
        return jsonify({"error": "channel is not voice_call"}), 400

    config = channel.config or {}
    expected_secret = config.get("callback_secret") or Config.VOICE_CALLBACK_SECRET

    if not expected_secret or secret != expected_secret:
        return jsonify({"error": "voice callback rejected"}), 403

    payload = request.get_json(silent=True)

    if payload is None:
        payload = request.form.to_dict(flat=True)

    provider_name = config.get("provider") or Config.VOICE_PROVIDER
    provider_config = resolve_env_values(config.get("provider_config") or {})
    provider = create_voice_provider(provider_name, provider_config)

    events = provider.parse_callback(
        payload=payload or {},
        headers=dict(request.headers),
        raw_body=request.get_data(),
        query_args=request.args.to_dict(flat=True),
    )

    if not events:
        return jsonify({"status": "ignored", "events": 0})

    processed = []

    for event in events:
        result = _process_voice_callback_event(channel, config, event)
        processed.append(result)

    return jsonify(
        {
            "status": "processed",
            "events": processed,
        }
    )


def _process_voice_callback_event(channel, config, event):
    """Process one normalized voice provider callback event."""

    notification = notifications_repo.get_notification_by_external_id(
        channel_id=channel.id,
        external_message_id=event.call_id,
    )

    if not notification:
        logging.getLogger("oncall.voice").warning(
            "voice callback notification not found",
            extra={
                "extra": {
                    "channel_id": channel.id,
                    "call_id": event.call_id,
                    "event_type": event.event_type,
                    "status": event.status,
                    "digit": event.digit,
                }
            },
        )

        return {
            "call_id": event.call_id,
            "status": "notification_not_found",
        }

    notifications_repo.update_notification_callback_state(
        notification=notification,
        event_type=event.event_type,
        provider_status=event.status,
        provider_payload=event.raw,
    )

    action = _resolve_voice_action(config, event)

    notifications_repo.create_notification_event(
        notification=notification,
        event_type=event.event_type,
        provider_status=event.status,
        digit=event.digit,
        action=action,
        message=event.message,
        payload=event.raw,
    )

    alert = notification.alert

    alerts_repo.create_alert_event(
        alert.id,
        f"voice_{event.event_type}",
        _voice_event_message(channel, event, action),
    )

    if action == "acknowledge":
        user_id = alert.assignee.id if alert.assignee else None
        acknowledge_alert(alert.id, user_id=user_id)

    elif action == "resolve":
        user_id = alert.assignee.id if alert.assignee else None
        resolve_alert(alert.id, user_id=user_id)

    return {
        "call_id": event.call_id,
        "event_type": event.event_type,
        "status": event.status,
        "digit": event.digit,
        "action": action,
        "alert_id": alert.id,
    }


def _resolve_voice_action(config, event):
    """Return alert action from provider event or DTMF digit."""

    if event.action in {"acknowledge", "resolve"}:
        return event.action

    if not event.digit:
        return None

    dtmf_actions = config.get("dtmf_actions") or {
        "1": "acknowledge",
        "2": "resolve",
    }

    return dtmf_actions.get(str(event.digit))


def _voice_event_message(channel, event, action):
    """Return human-readable alert history message."""

    parts = [
        f"Voice callback from {channel.name}",
        f"event={event.event_type}",
    ]

    if event.status:
        parts.append(f"status={event.status}")

    if event.digit:
        parts.append(f"digit={event.digit}")

    if action:
        parts.append(f"action={action}")

    return ", ".join(parts)
