from flask import Blueprint, jsonify, request

from app.modules.db import alerts_repo, notifications_repo
from app.services.alerts import acknowledge_alert, resolve_alert
from app.services.audit import write_audit
from app.services.rbac import get_allowed_team_ids, require_team_read, require_team_respond
from app.services.serializers import serialize_alert, serialize_alert_event

alerts_bp = Blueprint("alerts_api", __name__)


@alerts_bp.route("", methods=["GET"])
def list_alerts():
    """Return alerts with backend pagination, filters and sorting."""
    team_id = request.args.get("team_id", type=int)
    if team_id:
        error = require_team_read(team_id)
        if error:
            return error
        team_ids = None
    else:
        team_ids = get_allowed_team_ids()

    page = alerts_repo.paginate_alerts(
        team_id=team_id,
        team_ids=team_ids,
        status=request.args.get("status"),
        source=request.args.get("source"),
        severity=request.args.get("severity"),
        service_id=request.args.get("service_id", type=int),
        service_slug=request.args.get("service_slug"),
        service_status=request.args.get("service_status"),
        service_criticality=request.args.get("service_criticality"),
        search=request.args.get("search"),
        page=request.args.get("page", 1, type=int),
        page_size=request.args.get("page_size", 25, type=int),
        sort=request.args.get("sort", "activity"),
        order=request.args.get("order", "desc"),
    )
    return jsonify({
        "items": [serialize_alert(alert) for alert in page["items"]],
        "pagination": page["pagination"],
        "summary": page["summary"],
        "sort": page["sort"],
    })


@alerts_bp.route("/<int:alert_id>", methods=["GET"])
def get_alert(alert_id):
    """Return a single alert with payload, events and notification delivery records."""
    alert = alerts_repo.get_alert(alert_id)
    if alert.team_id:
        error = require_team_read(alert.team_id)
        if error:
            return error

    events = alerts_repo.list_alert_events(alert_id)
    notifications = notifications_repo.list_notifications_for_alert(alert_id)
    return jsonify(
        serialize_alert(
            alert,
            include_payload=True,
            include_details=True,
            events=events,
            notifications=notifications,
        )
    )


@alerts_bp.route("/<int:alert_id>/ack", methods=["POST"])
def ack_alert(alert_id):
    """Acknowledge an alert."""
    alert_before = alerts_repo.get_alert(alert_id)
    if alert_before.team_id:
        error = require_team_respond(alert_before.team_id)
        if error:
            return error

    data = request.json or {}
    user_id = data.get("user_id") or getattr(getattr(request, "current_user", None), "id", None)
    alert = acknowledge_alert(alert_id, user_id=user_id)
    write_audit(
        "alert.ack",
        object_type="alert",
        object_id=alert.id,
        team_id=alert.team.id if alert.team else None,
        user_id=user_id,
        data=data,
    )
    return jsonify(serialize_alert(alert))


@alerts_bp.route("/<int:alert_id>/resolve", methods=["POST"])
def resolve_alert_view(alert_id):
    """Resolve an alert."""
    alert_before = alerts_repo.get_alert(alert_id)
    if alert_before.team_id:
        error = require_team_respond(alert_before.team_id)
        if error:
            return error

    data = request.json or {}
    user_id = data.get("user_id") or getattr(getattr(request, "current_user", None), "id", None)
    alert = resolve_alert(alert_id, user_id=user_id)
    write_audit(
        "alert.resolve",
        object_type="alert",
        object_id=alert.id,
        team_id=alert.team.id if alert.team else None,
        user_id=user_id,
        data=data,
    )
    return jsonify(serialize_alert(alert))


@alerts_bp.route("/<int:alert_id>/events", methods=["GET"])
def list_alert_events(alert_id):
    """Return alert events."""
    alert = alerts_repo.get_alert(alert_id)
    if alert.team_id:
        error = require_team_read(alert.team_id)
        if error:
            return error

    return jsonify([
        serialize_alert_event(event)
        for event in alerts_repo.list_alert_events(alert_id)
    ])
