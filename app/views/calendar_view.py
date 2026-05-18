from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

from app.services.calendar_service import build_team_calendar
from app.services.rbac import parse_date_or_datetime, require_team_read

calendar_bp = Blueprint("calendar_api", __name__)

_DATE_FORMAT_MESSAGE = (
    "Invalid date or datetime format. Use ISO 8601 date or datetime, "
    "for example 2026-04-01 or 2026-04-01T00:00:00."
)


def _validation_detail(field, value, message, error_type="value_error"):
    """Build an API validation error detail for query parameters."""
    return {
        "field": field,
        "input": value,
        "loc": [field],
        "message": message,
        "type": error_type,
    }


def _validation_response(details):
    """Return a validation error response matching the common API shape."""
    return jsonify(
        {
            "details": details,
            "error": "validation_error",
            "message": "Request validation failed",
        }
    ), 400


def _parse_calendar_datetime(field, value):
    """Parse a calendar query datetime and return (value, validation_detail)."""
    if value in (None, ""):
        return None, None

    try:
        return parse_date_or_datetime(value), None
    except (TypeError, ValueError):
        return None, _validation_detail(
            field,
            value,
            _DATE_FORMAT_MESSAGE,
            error_type="datetime_parsing",
        )


@calendar_bp.route("", methods=["GET"])
def get_calendar():
    """Return on-call calendar events for a team."""
    team_id = request.args.get("team_id", type=int)
    if not team_id:
        return jsonify({"error": "team_id is required"}), 400

    start_raw = request.args.get("start") or datetime.utcnow().date().isoformat()
    end_raw = request.args.get("end")

    details = []
    start_at, start_error = _parse_calendar_datetime("start", start_raw)
    if start_error:
        details.append(start_error)

    end_at = None
    if end_raw:
        end_at, end_error = _parse_calendar_datetime("end", end_raw)
        if end_error:
            details.append(end_error)

    if details:
        return _validation_response(details)

    if end_at is None:
        end_at = start_at + timedelta(days=30)

    if end_at <= start_at:
        return _validation_response(
            [
                _validation_detail(
                    "end",
                    end_raw,
                    "end must be after start",
                )
            ]
        )

    error = require_team_read(team_id)
    if error:
        return error

    return jsonify(build_team_calendar(team_id, start_at, end_at))
