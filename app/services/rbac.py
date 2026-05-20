from flask import jsonify, request

from app.api.schemas.roles import (
    GROUP_EDITOR_ROLE,
    GROUP_USER_ADMIN_ROLE,
    GROUP_VIEWER_ROLE,
    TEAM_MANAGER_ROLE,
    TEAM_RESPONDER_ROLE,
    TEAM_VIEWER_ROLE,
)
from app.modules.db import groups_repo, teams_repo

GROUP_READ_ROLES = {GROUP_VIEWER_ROLE, GROUP_EDITOR_ROLE, GROUP_USER_ADMIN_ROLE}
GROUP_WRITE_ROLES = {GROUP_EDITOR_ROLE}
GROUP_USER_ADMIN_ROLES = {GROUP_USER_ADMIN_ROLE}

TEAM_READ_ROLES = {TEAM_VIEWER_ROLE, TEAM_RESPONDER_ROLE, TEAM_MANAGER_ROLE}
TEAM_RESPOND_ROLES = {TEAM_RESPONDER_ROLE, TEAM_MANAGER_ROLE}
TEAM_WRITE_ROLES = {TEAM_MANAGER_ROLE}


def current_user():
    """Return the current request user."""
    return getattr(request, "current_user", None)


def current_api_token():
    """Return the current request API token."""
    return getattr(request, "current_api_token", None)


def is_admin_user(user=None):
    """Return True when the current principal is an administrator."""
    user = user or current_user()
    return bool(user and user.is_admin)


def token_group_filter(group_ids):
    """Apply group restriction from the current API token."""
    api_token = current_api_token()
    if not api_token or not api_token.group_id:
        return group_ids
    return [group_id for group_id in group_ids if group_id == api_token.group_id]


def get_allowed_group_ids(user=None, write_required=False, manage_users_required=False, use_active_group=False):
    """Return group ids available to a user or personal API token.

    Active group is a UI filter, not a security boundary. If the selected active
    group is stale or inactive, it is ignored.
    """
    user = user or current_user()
    if not user:
        api_token = current_api_token()
        if api_token and api_token.group_id:
            return [api_token.group_id]
        return []

    if user.is_admin:
        groups = groups_repo.list_groups(active_only=True)
        group_ids = [group.id for group in groups]
        return token_group_filter(group_ids)

    groups = groups_repo.list_groups_for_user(
        user,
        write_required=write_required,
        manage_users_required=manage_users_required,
    )
    group_ids = [group.id for group in groups]

    if use_active_group and user.active_group_id and user.active_group_id in group_ids:
        return token_group_filter([user.active_group_id])
    return token_group_filter(group_ids)


def get_allowed_team_ids(user=None, write_required=False, respond_required=False, use_active_group=True):
    """Return team ids available to a user.

    Group access only defines the boundary. For regular users, access to a team
    also requires active TeamUser membership with an appropriate team role.
    """
    user = user or current_user()
    group_ids = get_allowed_group_ids(
        user=user,
        write_required=False,
        use_active_group=use_active_group,
    )
    if not group_ids:
        return []

    if not user:
        return [team.id for team in teams_repo.list_teams(active_only=True, group_ids=group_ids)]

    if user.is_admin:
        return [team.id for team in teams_repo.list_teams(active_only=True, group_ids=group_ids)]

    roles = TEAM_READ_ROLES
    if write_required:
        roles = TEAM_WRITE_ROLES
    elif respond_required:
        roles = TEAM_RESPOND_ROLES

    return [
        team.id
        for team in teams_repo.list_teams_for_user(
            user.id,
            roles=roles,
            group_ids=group_ids,
            active_only=True,
        )
    ]


def can_read_group(user, group_id):
    """Return True when a user can read a group."""
    if not user:
        return False
    if user.is_admin:
        return True
    return groups_repo.get_user_group_role(user.id, group_id) in GROUP_READ_ROLES


def can_write_group(user, group_id):
    """Return True when a user can create/edit group operational resources."""
    if not user:
        return False
    if user.is_admin:
        return True
    return groups_repo.get_user_group_role(user.id, group_id) in GROUP_WRITE_ROLES


def can_manage_group_users(user, group_id):
    """Return True when a user can manage users inside the group boundary."""
    if not user:
        return False
    if user.is_admin:
        return True
    return groups_repo.get_user_group_role(user.id, group_id) in GROUP_USER_ADMIN_ROLES


def can_read_team(user, team_id):
    """Return True when a user can read a team."""
    if not user:
        return False
    if user.is_admin:
        return True

    team = teams_repo.get_team(team_id)
    if not team.group_id:
        return False
    if not can_read_group(user, team.group_id):
        return False
    return teams_repo.get_user_team_role(user.id, team_id) in TEAM_READ_ROLES


def can_respond_team(user, team_id):
    """Return True when a user can acknowledge or resolve alerts for a team."""
    if not user:
        return False
    if user.is_admin:
        return True

    team = teams_repo.get_team(team_id)
    if not team.group_id:
        return False
    if not can_read_group(user, team.group_id):
        return False
    return teams_repo.get_user_team_role(user.id, team_id) in TEAM_RESPOND_ROLES


def can_write_team(user, team_id):
    """Return True when a user can write team resources."""
    if not user:
        return False
    if user.is_admin:
        return True

    team = teams_repo.get_team(team_id)
    if not team.group_id:
        return False
    if not can_read_group(user, team.group_id):
        return False
    return teams_repo.get_user_team_role(user.id, team_id) in TEAM_WRITE_ROLES


def require_admin_user():
    """Return an error response when current user is not an admin."""
    user = current_user()
    if not user or not user.is_admin:
        return jsonify({"error": "Admin role is required"}), 403
    return None


def require_group_write(group_id):
    """Return an error response when current user cannot write group resources."""
    if is_admin_user():
        return None
    if not can_write_group(current_user(), group_id):
        return jsonify({"error": "Group editor role is required for this group"}), 403
    return None


def require_group_user_admin(group_id):
    """Return an error response when current user cannot manage group users."""
    if is_admin_user():
        return None
    if not can_manage_group_users(current_user(), group_id):
        return jsonify({"error": "Group user admin role is required for this group"}), 403
    return None


def require_team_read(team_id):
    """Return an error response when current user cannot read a team."""
    if is_admin_user():
        return None
    if not can_read_team(current_user(), team_id):
        return jsonify({"error": "Access to this team is denied"}), 403
    return None


def require_team_respond(team_id):
    """Return an error response when current user cannot operate team alerts."""
    if is_admin_user():
        return None
    if not can_respond_team(current_user(), team_id):
        return jsonify({"error": "Team responder role is required for this team"}), 403
    return None


def require_team_write(team_id):
    """Return an error response when current user cannot write team resources."""
    if is_admin_user():
        return None
    if not can_write_team(current_user(), team_id):
        return jsonify({"error": "Team manager role is required for this team"}), 403
    return None


def require_permission(permission):
    """Backward-compatible permission decorator."""
    def decorator(func):
        from functools import wraps

        @wraps(func)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return jsonify({"error": "Authentication is required"}), 401
            if user.is_admin:
                return func(*args, **kwargs)
            if permission.startswith("admin:") or permission.endswith(":admin"):
                return jsonify({"error": "Admin role is required"}), 403
            if permission.endswith(":write") or permission in ("write", "rw"):
                if not get_allowed_group_ids(user, write_required=True):
                    return jsonify({"error": "Group editor role is required"}), 403
            return func(*args, **kwargs)

        return wrapper
    return decorator


def require_any_permission(*permissions):
    """Backward-compatible decorator for views that accept several permissions."""
    def decorator(func):
        from functools import wraps

        @wraps(func)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return jsonify({"error": "Authentication is required"}), 401
            if user.is_admin:
                return func(*args, **kwargs)

            for permission in permissions:
                if permission.startswith("admin:") or permission.endswith(":admin"):
                    continue
                if permission.endswith(":write") or permission in ("write", "rw"):
                    if get_allowed_group_ids(user, write_required=True):
                        return func(*args, **kwargs)
                elif get_allowed_group_ids(user, write_required=False):
                    return func(*args, **kwargs)

            return jsonify({"error": "Permission denied"}), 403

        return wrapper
    return decorator


def parse_date_or_datetime(value):
    """Parse an ISO date or datetime string."""
    from datetime import datetime, time

    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.combine(datetime.strptime(value, "%Y-%m-%d").date(), time.min)
