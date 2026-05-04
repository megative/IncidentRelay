from peewee import *
from playhouse.migrate import migrate

from app.db import init_database
from app.modules.db.migrator import get_migrator
from app.modules.db.models import AlertNotificationEvent

db = init_database()
migrator = get_migrator(db)


def _has_column(table_name, column_name):
    """Return True if table already has a column."""

    columns = db.get_columns(table_name)
    return any(column.name == column_name for column in columns)


def upgrade():
    """Apply voice callback storage changes."""

    operations = []

    if not _has_column("alertnotification", "provider_status"):
        operations.append(
            migrator.add_column(
                "alertnotification",
                "provider_status",
                CharField(null=True),
            )
        )

    if not _has_column("alertnotification", "provider_payload"):
        operations.append(
            migrator.add_column(
                "alertnotification",
                "provider_payload",
                TextField(null=True),
            )
        )

    if not _has_column("alertnotification", "last_callback_at"):
        operations.append(
            migrator.add_column(
                "alertnotification",
                "last_callback_at",
                DateTimeField(null=True),
            )
        )

    if not _has_column("alertnotification", "callback_count"):
        operations.append(
            migrator.add_column(
                "alertnotification",
                "callback_count",
                IntegerField(default=0),
            )
        )

    if operations:
        migrate(*operations)

    db.create_tables([AlertNotificationEvent], safe=True)

    try:
        db.execute_sql(
            "CREATE INDEX alertnotification_channel_external_message_id "
            "ON alertnotification (channel_id, external_message_id)"
        )
    except Exception:
        pass


def downgrade():
    """Rollback voice callback storage changes."""

    db.drop_tables([AlertNotificationEvent], safe=True)

    operations = []

    for column_name in [
        "provider_status",
        "provider_payload",
        "last_callback_at",
        "callback_count",
    ]:
        if _has_column("alertnotification", column_name):
            operations.append(
                migrator.drop_column("alertnotification", column_name)
            )

    if operations:
        migrate(*operations)
