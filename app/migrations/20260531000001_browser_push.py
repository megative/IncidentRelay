from app.db import database_proxy as db
from app.modules.db.models import (
    BrowserPushActionToken,
    BrowserPushSubscription,
)


def upgrade():
    db.create_tables(
        [
            BrowserPushSubscription,
            BrowserPushActionToken,
        ],
        safe=True,
    )


def downgrade():
    db.drop_tables(
        [
            BrowserPushActionToken,
            BrowserPushSubscription,
        ],
        safe=True,
    )
