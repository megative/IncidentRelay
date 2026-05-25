from flask import Blueprint, jsonify, request
from peewee import DoesNotExist, IntegrityError

from app.api.schemas.roles import GROUP_VIEWER_ROLE
from app.api.schemas.users import UserCreateSchema, UserUpdateSchema
from app.db import database_proxy as db
from app.login import hash_password
from app.modules.db import groups_repo, users_repo
from app.services.audit import write_audit
from app.services.rbac import require_admin_user, require_user_management_access, get_allowed_group_ids
from app.services.serializers import serialize_user
from app.services.validation import validate_body

admin_users_bp = Blueprint("admin_users_api", __name__)


def serialize_admin_user(user):
    """Serialize a user for the admin workspace with group membership metadata."""
    memberships = groups_repo.list_user_groups(user.id)
    data = serialize_user(user, groups=memberships)
    current_user = getattr(request, "current_user", None)
    data["is_current_user"] = bool(current_user and current_user.id == user.id)

    active_group_id = data.get("active_group_id")
    active_membership = None
    if active_group_id:
        for membership in memberships:
            if membership.group.id == active_group_id:
                active_membership = membership
                break
    elif memberships:
        active_membership = memberships[0]
        data["active_group_id"] = active_membership.group.id
        data["active_group_slug"] = active_membership.group.slug

    data["active_group_role"] = active_membership.role if active_membership else None
    return data


@admin_users_bp.route("", methods=["GET"])
def admin_list_users():
    """Return users for the admin workspace."""
    access_error = require_user_management_access()
    if access_error:
        return access_error

    user = request.current_user

    if user.is_admin:
        users = users_repo.list_users()
    else:
        group_ids = get_allowed_group_ids(
            user=user,
            manage_users_required=True,
            use_active_group=True,
        )
        users = users_repo.list_users_by_group_ids(group_ids)

    return jsonify([serialize_admin_user(item) for item in users])


@admin_users_bp.route("", methods=["POST"])
def admin_create_user():
    """Create a user and optionally add it to a group. Global admin only."""
    admin_error = require_admin_user()
    if admin_error:
        return admin_error

    payload, error = validate_body(UserCreateSchema)
    if error:
        return error

    data = payload.model_dump()
    group_id = data.pop("group_id", None)
    group_role = data.pop("group_role", GROUP_VIEWER_ROLE)
    password = data.pop("password", None)
    if password:
        data["password_hash"] = hash_password(password)

    group = None
    if group_id:
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

    try:
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
    except IntegrityError:
        return jsonify({
            "error": "user_conflict",
            "message": "User with this username or unique field already exists",
        }), 409

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
    return jsonify(serialize_admin_user(user)), 201


@admin_users_bp.route("/<int:user_id>", methods=["GET"])
def admin_get_user(user_id):
    """Return one user for the admin workspace."""
    admin_error = require_admin_user()
    if admin_error:
        return admin_error
    return jsonify(serialize_admin_user(users_repo.get_user(user_id)))


@admin_users_bp.route("/<int:user_id>", methods=["PUT"])
def admin_update_user(user_id):
    """Update a user from the admin workspace."""
    admin_error = require_admin_user()
    if admin_error:
        return admin_error

    payload, error = validate_body(UserUpdateSchema)
    if error:
        return error

    data = payload.model_dump()
    group_update_requested = "group_id" in payload.model_fields_set
    group_id = data.pop("group_id", None)
    group_role = data.pop("group_role", GROUP_VIEWER_ROLE)

    if request.current_user and request.current_user.id == user_id and data.get("active") is False:
        return jsonify({
            "error": "self_deactivation_denied",
            "message": "You cannot disable your own user account",
        }), 400

    group = None
    if group_update_requested and group_id:
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

    password = data.pop("password", None)
    if password:
        data["password_hash"] = hash_password(password)

    try:
        with db.atomic():
            user = users_repo.update_user(user_id, data)
            if group_update_requested:
                if group_id:
                    groups_repo.add_user_to_group(
                        user_id=user.id,
                        group_id=group_id,
                        role=group_role,
                    )
                    users_repo.set_active_group(user.id, group_id)
                else:
                    users_repo.set_active_group(user.id, None)
            user = users_repo.get_user(user.id)
    except IntegrityError:
        return jsonify({
            "error": "user_conflict",
            "message": "User with this username or unique field already exists",
        }), 409

    audit_payload = {**data, "password_hash": "***" if password else None}
    if group_update_requested:
        audit_payload["group_id"] = group_id
        audit_payload["group_role"] = group_role if group_id else None

    write_audit(
        "admin.user.update",
        object_type="user",
        object_id=user.id,
        group_id=group.id if group else None,
        data=audit_payload,
    )
    return jsonify(serialize_admin_user(user))


@admin_users_bp.route("/<int:user_id>", methods=["DELETE"])
def admin_delete_user(user_id):
    """Remove a user from the admin workspace."""
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
