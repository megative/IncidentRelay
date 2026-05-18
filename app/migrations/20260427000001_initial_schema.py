from app.db import init_database
from app.modules.db.models import (
    ApiToken,
    Alert,
    AlertEvent,
    AlertNotification,
    AlertNotificationEvent,
    AlertRoute,
    AlertRouteChannel,
    Group,
    AppLock,
    AuditLog,
    Migration,
    MigrationState,
    NotificationChannel,
    Role,
    Rotation,
    RotationMember,
    RotationOverride,
    Silence,
    Team,
    UserGroup,
    TeamUser,
    User,
    UserRole,
)

db = init_database()

MODELS = [
    Migration,
    MigrationState,
    Group,
    User,
    UserGroup,
    Role,
    UserRole,
    Team,
    TeamUser,
    Rotation,
    RotationMember,
    RotationOverride,
    NotificationChannel,
    AlertRoute,
    AlertRouteChannel,
    Alert,
    AlertEvent,
    AlertNotification,
    AlertNotificationEvent,
    Silence,
    ApiToken,
    AuditLog,
    AppLock,
]


def upgrade():
    """
    Create the initial database schema.
    """
    db.create_tables(MODELS, safe=True)


def downgrade():
    """
    Drop all application tables.
    """
    db.drop_tables(list(reversed(MODELS)), safe=True)
