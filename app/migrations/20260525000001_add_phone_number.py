from peewee import CharField
from playhouse.migrate import migrate

from app.db import init_database
from app.modules.db.migrator import get_migrator
from app.modules.db.models import SsoProvider


db = init_database()
migrator = get_migrator(db)


def upgrade():
    """
    Add phone claim mapping to SSO providers.
    """
    migrate(
        migrator.add_column(
            SsoProvider._meta.table_name,
            "phone_claim",
            CharField(null=True),
        ),
    )

    SsoProvider.update(phone_claim="phone_number").where(
        SsoProvider.phone_claim.is_null(True)
    ).execute()


def downgrade():
    """
    Remove phone claim mapping from SSO providers.
    """
    migrate(
        migrator.drop_column(
            SsoProvider._meta.table_name,
            "phone_claim",
        ),
    )
