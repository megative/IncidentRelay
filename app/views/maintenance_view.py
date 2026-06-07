from flask import Blueprint, jsonify, request
from datetime import datetime, timezone

from app.services.validation import validate_body
from app.api.schemas.maintenance_windows import (
    MaintenanceWindowCreateSchema,
    MaintenanceWindowExtendSchema,
    MaintenanceWindowUpdateSchema,
)
from app.modules.db import maintenance_repo
from app.services.maintenance import (
    cancel_maintenance_window,
    create_maintenance_window,
    delete_maintenance_window,
    update_maintenance_window,
)
from app.services.serializers import serialize_maintenance_window
from app.services.rbac import current_user, require_team_read, require_team_write
from app.services.audit import write_audit

maintenance_bp = Blueprint("maintenance_api", __name__)


def _current_user_id():
    user = getattr(request, "current_user", None)

    if not user:
        raise PermissionError("authentication required")

    return user.id


def _maintenance_audit_data(window, payload=None):
    data = {
        "name": window.name,
        "status": window.status,
        "behavior": window.behavior,
        "timezone": window.timezone,
        "starts_at": window.starts_at.isoformat() if window.starts_at else None,
        "ends_at": window.ends_at.isoformat() if window.ends_at else None,
        "enabled": window.enabled,
        "deleted": window.deleted,
    }

    if getattr(window, "rrule", None):
        data["rrule"] = window.rrule

    if payload:
        data["payload"] = payload

    return data


def _write_maintenance_audit(action, window, payload=None):
    user = getattr(request, "current_user", None)

    write_audit(
        action,
        object_type="maintenance_window",
        object_id=window.id,
        group_id=window.group_id,
        team_id=window.team_id,
        user_id=user.id if user else None,
        data=_maintenance_audit_data(window, payload),
    )


def _request_user():
    return getattr(request, "current_user", None) or current_user()


def _request_user_id():
    user = _request_user()
    return getattr(user, "id", None)


def _json_error(error, message, status_code):
    return jsonify({
        "error": error,
        "message": message,
    }), status_code


def _check_window_read(window):
    for scope in window.scopes:
        if scope.team_id:
            error = require_team_read(scope.team_id)
            if error:
                return error

        if scope.service_id and scope.service:
            error = require_team_read(scope.service.team_id)
            if error:
                return error

        if scope.route_id and scope.route:
            error = require_team_read(scope.route.team_id)
            if error:
                return error

    return None


def _check_window_write(window):
    for scope in window.scopes:
        if scope.team_id:
            error = require_team_write(scope.team_id)
            if error:
                return error

        if scope.service_id and scope.service:
            error = require_team_write(scope.service.team_id)
            if error:
                return error

        if scope.route_id and scope.route:
            error = require_team_write(scope.route.team_id)
            if error:
                return error

    return None


def _check_payload_write_scope(payload):
    for scope in payload.get("scopes") or []:
        if scope.get("team_id"):
            error = require_team_write(scope["team_id"])
            if error:
                return error

    return None


def _maintenance_window_payload_data(payload):
    """Convert validated maintenance window payload to repository data."""
    return {
        "service_id": payload.service_id,
        "title": payload.title,
        "description": payload.description,
        "start_at": payload.start_at,
        "end_at": payload.end_at,
        "enabled": payload.enabled,
    }


@maintenance_bp.route("", methods=["GET"])
def list_maintenance_windows():
    team_id = request.args.get("team_id", type=int)
    service_id = request.args.get("service_id", type=int)
    route_id = request.args.get("route_id", type=int)
    group_id = request.args.get("group_id", type=int)

    if team_id:
        error = require_team_read(team_id)
        if error:
            return error

    windows = maintenance_repo.list_maintenance_windows(
        group_id=group_id,
        team_id=team_id,
        service_id=service_id,
        route_id=route_id,
        include_deleted=request.args.get("include_deleted") == "1",
        include_finished=request.args.get("include_finished", "1") == "1",
    )

    visible = []

    for window in windows:
        error = _check_window_read(window)
        if not error:
            visible.append(window)

    return jsonify([
        serialize_maintenance_window(window)
        for window in visible
    ])


@maintenance_bp.route("", methods=["POST"])
def create_window():
    payload = request.get_json(silent=True) or {}

    try:
        window = create_maintenance_window(
            payload,
            user_id=_current_user_id(),
        )
    except ValueError as exc:
        return jsonify({"error": "validation_error", "message": str(exc)}), 400
    except PermissionError as exc:
        return jsonify({"error": "forbidden", "message": str(exc)}), 403

    _write_maintenance_audit(
        "maintenance_window.create",
        window,
        payload,
    )

    return jsonify(serialize_maintenance_window(window)), 201


@maintenance_bp.route("/<int:window_id>", methods=["GET"])
def get_window(window_id):
    window = maintenance_repo.get_maintenance_window(window_id)

    if not window:
        return _json_error("not_found", "Maintenance window not found", 404)

    error = _check_window_read(window)
    if error:
        return error

    return jsonify(serialize_maintenance_window(window))


@maintenance_bp.route("/<int:window_id>", methods=["PUT"])
def update_window(window_id):
    payload = request.get_json(silent=True) or {}

    try:
        window = update_maintenance_window(
            window_id,
            payload,
            user_id=_current_user_id(),
        )
    except ValueError as exc:
        return jsonify({"error": "validation_error", "message": str(exc)}), 400
    except PermissionError as exc:
        return jsonify({"error": "forbidden", "message": str(exc)}), 403
    except LookupError as exc:
        return jsonify({"error": "not_found", "message": str(exc)}), 404

    _write_maintenance_audit(
        "maintenance_window.update",
        window,
        payload,
    )

    return jsonify(serialize_maintenance_window(window))


@maintenance_bp.route("/<int:window_id>/cancel", methods=["POST"])
def cancel_window(window_id):
    payload = request.get_json(silent=True) or {}

    try:
        window = cancel_maintenance_window(
            window_id,
            payload,
            user_id=_current_user_id(),
        )
    except ValueError as exc:
        return jsonify({"error": "validation_error", "message": str(exc)}), 400
    except PermissionError as exc:
        return jsonify({"error": "forbidden", "message": str(exc)}), 403
    except LookupError as exc:
        return jsonify({"error": "not_found", "message": str(exc)}), 404

    _write_maintenance_audit(
        "maintenance_window.cancel",
        window,
        payload,
    )

    return jsonify(serialize_maintenance_window(window))


@maintenance_bp.route("/<int:window_id>", methods=["DELETE"])
def delete_window(window_id):
    try:
        window = delete_maintenance_window(
            window_id,
            user_id=_current_user_id(),
        )
    except PermissionError as exc:
        return jsonify({"error": "forbidden", "message": str(exc)}), 403
    except LookupError as exc:
        return jsonify({"error": "not_found", "message": str(exc)}), 404

    _write_maintenance_audit(
        "maintenance_window.delete",
        window,
        {"deleted": True},
    )

    return jsonify({"deleted": True, "id": window.id})
