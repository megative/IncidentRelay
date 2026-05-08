from peewee import CharField
from playhouse.migrate import migrate

from app.db import init_database
from app.modules.db.migrator import get_migrator
from app.modules.db.models import User


db = init_database()
migrator = get_migrator(db)


def table_exists(table_name):
    """
    Return True when a table exists.
    """
    return table_name in db.get_tables()


def has_column(table_name, column_name):
    """
    Return True when a table has a column.
    """
    if not table_exists(table_name):
        return False

    return any(
        column.name == column_name
        for column in db.get_columns(table_name)
    )


def upgrade():
    """
    Replace user.telegram_chat_id with user.telegram_user_id.

    telegram_chat_id stored chat destinations and is not needed anymore.
    telegram_user_id stores Telegram callback_query.from.id and is used to
    identify who clicked ACK/Resolve buttons.
    """
    table_name = User._meta.table_name
    operations = []

    if not has_column(table_name, "telegram_user_id"):
        operations.append(
            migrator.add_column(
                table_name,
                "telegram_user_id",
                CharField(null=True),
            )
        )

    if has_column(table_name, "telegram_chat_id"):
        operations.append(
            migrator.drop_column(table_name, "telegram_chat_id")
        )

    if operations:
        migrate(*operations)


def downgrade():
    """
    Restore user.telegram_chat_id and remove user.telegram_user_id.
    """
    table_name = User._meta.table_name
    operations = []

    if not has_column(table_name, "telegram_chat_id"):
        operations.append(
            migrator.add_column(
                table_name,
                "telegram_chat_id",
                CharField(null=True),
            )
        )

    if has_column(table_name, "telegram_user_id"):
        operations.append(
            migrator.drop_column(table_name, "telegram_user_id")
        )

    if operations:
        migrate(*operations)
