from peewee import DateTimeField
from playhouse.migrate import migrate

from app.db import init_database
from app.modules.db.migrator import get_migrator
from app.modules.db.models import Alert


db = init_database()
migrator = get_migrator(db)


def table_exists(table_name):
    """Return True when a table exists."""
    return table_name in db.get_tables()


def has_column(table_name, column_name):
    """Return True when a table has a column."""
    if not table_exists(table_name):
        return False

    return any(
        column.name == column_name
        for column in db.get_columns(table_name)
    )


def upgrade():
    """Add resolved_at timestamp to alerts."""
    table_name = Alert._meta.table_name
    operations = []

    if not has_column(table_name, "resolved_at"):
        operations.append(
            migrator.add_column(
                table_name,
                "resolved_at",
                DateTimeField(null=True),
            )
        )

    if operations:
        migrate(*operations)


def downgrade():
    """Remove resolved_at timestamp from alerts."""
    table_name = Alert._meta.table_name
    operations = []

    if has_column(table_name, "resolved_at"):
        operations.append(
            migrator.drop_column(table_name, "resolved_at")
        )

    if operations:
        migrate(*operations)
