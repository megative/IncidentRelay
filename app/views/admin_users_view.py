from flask import Blueprint, jsonify, request
from peewee import DoesNotExist

from app.login import hash_password
from app.db import database_proxy as db
from app.api.schemas.users import UserUpdateSchema, UserCreateSchema
from app.modules.db import users_repo, groups_repo
from app.services.audit import write_audit
from app.services.rbac import require_admin_user, require_permission, require_group_write
from app.services.serializers import serialize_user
from app.services.validation import validate_body


admin_users_bp = Blueprint("admin_users_api", __name__)


@admin_users_bp.route("", methods=["GET"])
@require_permission("users:admin")
def admin_list_users():
    """
    Return users for the admin workspace.
    """

    return jsonify([serialize_user(user) for user in users_repo.list_users()])


@admin_users_bp.route("", methods=["POST"])
@require_permission("users:admin")
def admin_create_user():
    """Create a user and optionally add it to a group."""

    payload, error = validate_body(UserCreateSchema)
    if error:
        return error

    data = payload.model_dump()

    group_id = data.pop("group_id", None)
    group_role = data.pop("group_role", "read_only")

    password = data.pop("password", None)
    if password:
        data["password_hash"] = hash_password(password)

    group = None
    if group_id:
        error = require_group_write(group_id)
        if error:
            return error

        try:
            group = groups_repo.get_group(group_id)
        except DoesNotExist:
            return jsonify({
                "error": "group_not_found",
                "message": "Selected group was not found",
            }), 404

        if not group.active:
            return jsonify({
                "error": "group_inactive",
                "message": "Selected group is inactive",
            }), 400

    with db.atomic():
        user = users_repo.create_user(**data)

        if group_id:
            groups_repo.add_user_to_group(
                user_id=user.id,
                group_id=group_id,
                role=group_role,
            )
            users_repo.set_active_group(user.id, group_id)
            user = users_repo.get_user(user.id)

    audit_data = {
        **data,
        "password_hash": "***" if password else None,
        "group_id": group_id,
        "group_role": group_role if group_id else None,
    }

    write_audit(
        "user.create",
        object_type="user",
        object_id=user.id,
        group_id=group.id if group else None,
        data=audit_data,
    )

    return jsonify(serialize_user(user)), 201


@admin_users_bp.route("/<int:user_id>", methods=["GET"])
@require_permission("users:admin")
def admin_get_user(user_id):
    """
    Return one user for the admin workspace.
    """

    return jsonify(serialize_user(users_repo.get_user(user_id)))


@admin_users_bp.route("/<int:user_id>", methods=["PUT"])
@require_permission("users:admin")
def admin_update_user(user_id):
    """
    Update a user from the admin workspace.
    """

    admin_error = require_admin_user()
    if admin_error:
        return admin_error

    payload, error = validate_body(UserUpdateSchema)
    if error:
        return error

    data = payload.model_dump()
    password = data.pop("password", None)

    if password:
        data["password_hash"] = hash_password(password)

    user = users_repo.update_user(user_id, data)
    write_audit("admin.user.update", object_type="user", object_id=user.id, data={**data, "password_hash": "***" if password else None})
    return jsonify(serialize_user(user))


@admin_users_bp.route("/<int:user_id>", methods=["DELETE"])
@require_permission("users:admin")
def admin_delete_user(user_id):
    """
    Remove a user from the admin workspace.

    This is a soft-delete. Historical alerts remain safe, but memberships,
    rotations and personal API tokens are revoked.
    """
    admin_error = require_admin_user()
    if admin_error:
        return admin_error

    if request.current_user and request.current_user.id == user_id:
        return jsonify({"error": "You cannot remove your own user account"}), 400

    try:
        user = users_repo.soft_delete_user(user_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 409

    if not user:
        return jsonify({"error": "User not found"}), 404

    write_audit(
        "admin.user.remove",
        object_type="user",
        object_id=user.id,
        data={
            "username": user.username,
            "historical_alerts_preserved": True,
            "api_tokens_revoked": True,
            "memberships_removed": True,
        },
    )

    return jsonify({
        "deleted": True,
        "id": user.id,
        "username": user.username,
    })

