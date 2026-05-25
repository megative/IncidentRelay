"""Canonical RBAC role names used by schemas, services and OpenAPI."""

SSO_GLOBAL_ADMIN_ROLE = "global_admin"

GROUP_VIEWER_ROLE = "viewer"
GROUP_EDITOR_ROLE = "editor"
GROUP_USER_ADMIN_ROLE = "user_admin"

GROUP_ROLE_VALUES = (
    GROUP_VIEWER_ROLE,
    GROUP_EDITOR_ROLE,
    GROUP_USER_ADMIN_ROLE,
)
GROUP_ASSIGNABLE_BY_USER_ADMIN_VALUES = (
    GROUP_VIEWER_ROLE,
    GROUP_EDITOR_ROLE,
)
GROUP_ROLE_PATTERN = r"^(viewer|editor|user_admin)$"
GROUP_ASSIGNABLE_BY_USER_ADMIN_PATTERN = r"^(viewer|editor)$"

TEAM_VIEWER_ROLE = "viewer"
TEAM_RESPONDER_ROLE = "responder"
TEAM_MANAGER_ROLE = "manager"

TEAM_ROLE_VALUES = (
    TEAM_VIEWER_ROLE,
    TEAM_RESPONDER_ROLE,
    TEAM_MANAGER_ROLE,
)
TEAM_ROLE_PATTERN = r"^(viewer|responder|manager)$"
