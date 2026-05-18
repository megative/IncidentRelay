import json
from json import JSONDecodeError

from flask import jsonify, request
from pydantic import ValidationError


def make_json_safe(value):
    """Convert values from Pydantic errors to JSON-serializable values."""
    if isinstance(value, BaseException):
        return str(value)
    if isinstance(value, dict):
        return {str(key): make_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [make_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def normalize_validation_error(error):
    """Convert one Pydantic error to a clean API error object."""
    loc = [str(item) for item in error.get("loc", [])]
    message = error.get("msg", "Invalid value")

    if message.startswith("Value error, "):
        message = message.replace("Value error, ", "", 1)

    result = {
        "field": ".".join(loc) if loc else None,
        "loc": loc,
        "message": message,
        "type": error.get("type"),
    }

    if "input" in error:
        result["input"] = make_json_safe(error["input"])
    if "ctx" in error:
        result["ctx"] = make_json_safe(error["ctx"])

    return result


def make_body_validation_detail(message, error_type, input_value=None):
    """Build a validation detail for request body level errors."""
    detail = {
        "field": "body",
        "loc": ["body"],
        "message": message,
        "type": error_type,
    }

    if input_value is not None:
        detail["input"] = make_json_safe(input_value)

    return detail


def make_validation_response(message, details):
    """Build a normalized validation error response."""
    return (
        jsonify({
            "error": "validation_error",
            "message": message,
            "details": details,
        }),
        400,
    )


def validate_body(schema_cls):
    """Validate JSON request body with a Pydantic schema."""
    raw_body = request.get_data(cache=True) or b""

    if not raw_body.strip():
        message = "Request body is required"
        return None, make_validation_response(
            message,
            [make_body_validation_detail(message, "missing")],
        )

    raw_text = raw_body.decode("utf-8", errors="replace")

    try:
        payload = json.loads(raw_text)
    except JSONDecodeError:
        message = "Request body must be valid JSON"
        return None, make_validation_response(
            message,
            [make_body_validation_detail(message, "json_invalid", raw_text)],
        )

    try:
        return schema_cls.model_validate(payload), None
    except ValidationError as exc:
        return None, make_validation_response(
            "Request validation failed",
            [normalize_validation_error(error) for error in exc.errors()],
        )
