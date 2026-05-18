"""Rename RBAC roles and split group/team permissions."""

from app.modules.db.models import TeamUser, UserGroup


def upgrade():
    """Migrate legacy read_only/rw/member roles to the new RBAC names."""
    UserGroup.update(role="viewer").where(UserGroup.role == "read_only").execute()
    UserGroup.update(role="editor").where(UserGroup.role == "rw").execute()

    TeamUser.update(role="viewer").where(TeamUser.role == "read_only").execute()
    TeamUser.update(role="responder").where(TeamUser.role == "member").execute()
    TeamUser.update(role="manager").where(TeamUser.role == "rw").execute()


def downgrade():
    """Rollback new RBAC names to the closest legacy roles."""
    UserGroup.update(role="read_only").where(UserGroup.role == "viewer").execute()
    UserGroup.update(role="rw").where(UserGroup.role == "editor").execute()
    UserGroup.update(role="rw").where(UserGroup.role == "user_admin").execute()

    TeamUser.update(role="read_only").where(TeamUser.role == "viewer").execute()
    TeamUser.update(role="member").where(TeamUser.role == "responder").execute()
    TeamUser.update(role="rw").where(TeamUser.role == "manager").execute()
