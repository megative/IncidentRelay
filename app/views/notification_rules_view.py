from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from app.api.schemas.notification_rules import (
    NotificationRuleCreateSchema,
    NotificationRuleUpdateSchema,
)
from app.services import notification_rules

notification_rules_bp = Blueprint("notification_rules_api", __name__)


@notification_rules_bp.route("/profile/notification-rules", methods=["GET"])
def list_profile_notification_rules():
    return jsonify(
        notification_rules.list_user_rules(request.current_user)
    )


@notification_rules_bp.route("/profile/notification-rules", methods=["POST"])
def create_profile_notification_rule():
    payload = request.get_json(silent=True) or {}

    try:
        data = NotificationRuleCreateSchema.model_validate(payload)
        rule = notification_rules.create_user_rule(
            request.current_user,
            method=data.method,
            delay_seconds=data.delay_seconds,
            severities=data.severities,
            event_types=data.event_types,
            enabled=data.enabled,
        )
    except ValidationError as exc:
        return jsonify(
            {
                "error": "validation_error",
                "message": "Request validation failed",
                "details": exc.errors(),
            }
        ), 400
    except ValueError as exc:
        return jsonify(
            {
                "error": "validation_error",
                "message": str(exc),
            }
        ), 400

    return jsonify(notification_rules.serialize_rule(rule)), 201


@notification_rules_bp.route("/profile/notification-rules/<int:rule_id>", methods=["PUT"])
def update_profile_notification_rule(rule_id):
    payload = request.get_json(silent=True) or {}

    try:
        data = NotificationRuleUpdateSchema.model_validate(payload)
        rule = notification_rules.update_user_rule(
            request.current_user,
            rule_id,
            data.model_dump(exclude_unset=True),
        )
    except ValidationError as exc:
        return jsonify(
            {
                "error": "validation_error",
                "message": "Request validation failed",
                "details": exc.errors(),
            }
        ), 400
    except ValueError as exc:
        return jsonify(
            {
                "error": "validation_error",
                "message": str(exc),
            }
        ), 400

    return jsonify(notification_rules.serialize_rule(rule))


@notification_rules_bp.route("/profile/notification-rules/<int:rule_id>", methods=["DELETE"])
def delete_profile_notification_rule(rule_id):
    try:
        rule = notification_rules.delete_user_rule(
            request.current_user,
            rule_id,
        )
    except ValueError as exc:
        return jsonify(
            {
                "error": "not_found",
                "message": str(exc),
            }
        ), 404

    return jsonify(
        {
            "deleted": True,
            "id": rule.id,
        }
    )
