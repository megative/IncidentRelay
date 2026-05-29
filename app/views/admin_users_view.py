from flask import Blueprint, jsonify, request
from peewee import DoesNotExist, IntegrityError

from app.api.schemas.users import UserCreateSchema, UserUpdateSchema
from app.db import database_proxy as db
from app.login import hash_password
from app.modules.db import groups_repo, users_repo
from app.services.audit import write_audit
from app.services.serializers import serialize_user
from app.services.validation import validate_body
from app.api.schemas.roles import (
    GROUP_USER_ADMIN_ROLE,
    GROUP_VIEWER_ROLE,
)
from app.services.rbac import (
    get_allowed_group_ids,
    is_global_admin_user,
    require_admin_user,
    require_assign_group_role,
    require_user_management_access,
)

admin_users_bp = Blueprint("admin_users_api", __name__)


def _managed_group_ids():
    """Return group ids where current user can manage users."""
    return get_allowed_group_ids(
        manage_users_required=True,
        use_active_group=False,
    )


def _user_memberships_in_groups(user_id, group_ids):
    """Return memberships for selected groups only."""
    allowed = set(group_ids or [])

    return [
        membership
        for membership in groups_repo.list_user_groups(user_id)
        if membership.group.id in allowed
    ]


def _require_user_in_managed_group(user_id):
    """Return target user and visible memberships or error."""
    managed_group_ids = _managed_group_ids()
    memberships = _user_memberships_in_groups(user_id, managed_group_ids)

    if not memberships:
        return None, None, (
            jsonify({
                "error": "user_access_denied",
                "message": "User is not in a group you can manage",
            }),
            403,
        )

    user = users_repo.get_user(user_id)

    if user.is_admin:
        return None, None, (
            jsonify({
                "error": "admin_user_readonly",
                "message": "Group user admins cannot edit global administrators",
            }),
            403,
        )

    return user, memberships, None


def _validate_group_user_admin_assignment(group_id, group_role):
    """Validate group assignment for non-global user admins."""
    managed_group_ids = _managed_group_ids()

    if not group_id:
        if len(managed_group_ids) == 1:
            return managed_group_ids[0], group_role, None

        return None, None, (
            jsonify({
                "error": "group_required",
                "message": "Group is required",
            }),
            400,
        )

    if group_id not in managed_group_ids:
        return None, None, (
            jsonify({
                "error": "group_access_denied",
                "message": "You cannot manage users in this group",
            }),
            403,
        )

    role_error = require_assign_group_role(group_role)
    if role_error:
        return None, None, role_error

    return group_id, group_role, None


def serialize_admin_user(user, memberships=None):
    """Serialize a user for the users workspace with group membership metadata."""
    if memberships is None:
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

    if active_membership:
        data["active_group_id"] = active_membership.group.id
        data["active_group_slug"] = active_membership.group.slug
        data["active_group_role"] = active_membership.role
    else:
        data["active_group_id"] = None
        data["active_group_slug"] = None
        data["active_group_role"] = None

    return data


@admin_users_bp.route("", methods=["GET"])
def admin_list_users():
    """Return users for the users workspace."""
    error = require_user_management_access()
    if error:
        return error

    if is_global_admin_user():
        return jsonify([
            serialize_admin_user(user)
            for user in users_repo.list_users()
        ])

    managed_group_ids = _managed_group_ids()

    users = users_repo.list_users_by_group_ids(
        managed_group_ids,
        active_only=False,
    )

    result = []

    for user in users:
        memberships = _user_memberships_in_groups(
            user.id,
            managed_group_ids,
        )
        result.append(serialize_admin_user(user, memberships=memberships))

    return jsonify(result)


@admin_users_bp.route("", methods=["POST"])
def admin_create_user():
    """Create a user and optionally add it to a group. Global admin only."""
    error = require_user_management_access()
    if error:
        return error

    payload, error = validate_body(UserCreateSchema)
    if error:
        return error

    data = payload.model_dump()
    group_id = data.pop("group_id", None)
    group_role = data.pop("group_role", GROUP_VIEWER_ROLE)
    password = data.pop("password", None)
    if password:
        data["password_hash"] = hash_password(password)

    if not is_global_admin_user():
        group_id, group_role, error = _validate_group_user_admin_assignment(
            group_id,
            group_role,
        )
        if error:
            return error

        if data.get("is_admin"):
            return jsonify({
                "error": "admin_role_not_allowed",
                "message": "Only global admin can create global administrators",
            }), 403

        data["is_admin"] = False
        data["active"] = True

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
    """Update a user from the users workspace."""
    error = require_user_management_access()
    if error:
        return error

    payload, error = validate_body(UserUpdateSchema)
    if error:
        return error

    data = payload.model_dump()
    group_update_requested = "group_id" in payload.model_fields_set
    group_id = data.pop("group_id", None)
    group_role = data.pop("group_role", GROUP_VIEWER_ROLE)

    if is_global_admin_user():
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

    target_user, memberships, error = _require_user_in_managed_group(user_id)
    if error:
        return error

    if data.get("is_admin"):
        return jsonify({
            "error": "admin_role_not_allowed",
            "message": "Only global admin can assign global administrator access",
        }), 403

    data["is_admin"] = False

    # Group user-admin must not globally enable/disable users.
    # Group membership active flag is managed from the Groups page.
    data.pop("active", None)

    if group_update_requested:
        group_id, group_role, error = _validate_group_user_admin_assignment(
            group_id,
            group_role,
        )
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
    else:
        group = memberships[0].group if memberships else None

    password = data.pop("password", None)
    if password:
        data["password_hash"] = hash_password(password)

    try:
        with db.atomic():
            user = users_repo.update_user(user_id, data)

            if group_update_requested:
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

    visible_memberships = _user_memberships_in_groups(
        user.id,
        _managed_group_ids(),
    )

    audit_payload = {**data, "password_hash": "***" if password else None}

    if group_update_requested:
        audit_payload["group_id"] = group_id
        audit_payload["group_role"] = group_role

    write_audit(
        "group.user.profile.update",
        object_type="user",
        object_id=user.id,
        group_id=group.id if group else None,
        data=audit_payload,
    )

    return jsonify(serialize_admin_user(user, memberships=visible_memberships))


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
