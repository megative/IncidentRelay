from peewee import CharField
from playhouse.migrate import migrate

from app.db import init_database
from app.modules.db.migrator import get_migrator
from app.modules.db.models import SsoProvider


db = init_database()
migrator = get_migrator(db)


def upgrade():
    """
    Add IdP metadata URL to SSO providers.
    """
    migrate(
        migrator.add_column(
            SsoProvider._meta.table_name,
            "saml_idp_metadata_url",
            CharField(null=True, max_length=2048),
        ),
    )


def downgrade():
    """
    Remove IdP metadata URL from SSO providers.
    """
    migrate(
        migrator.drop_column(
            SsoProvider._meta.table_name,
            "saml_idp_metadata_url",
        ),
    )
