from flask import jsonify


def unique_field_conflict(field, value, message):
    """Return a unique field conflict response."""
    return jsonify({
        "error": "conflict",
        "message": message,
        "details": [
            {
                "field": field,
                "loc": [field],
                "message": f"{field} must be unique",
                "type": "unique",
                "input": value,
            }
        ],
    }), 409


def integrity_conflict(message):
    """Return a generic integrity conflict response."""
    return jsonify({
        "error": "conflict",
        "message": message,
        "details": [
            {
                "message": "Database integrity constraint failed",
                "type": "integrity_error",
            }
        ],
    }), 409
