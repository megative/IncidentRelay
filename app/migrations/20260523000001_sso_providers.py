from app.db import init_database
from app.modules.db.models import (
    SsoProvider,
    SsoIdentity,
    SsoGroupMapping,
)

db = init_database()

MODELS = [
    SsoProvider,
    SsoIdentity,
    SsoGroupMapping,
]


def upgrade():
    """Create SSO provider, identity and group mapping tables."""
    db.create_tables(MODELS, safe=True)


def downgrade():
    """Drop SSO tables."""
    db.drop_tables(list(reversed(MODELS)), safe=True)
