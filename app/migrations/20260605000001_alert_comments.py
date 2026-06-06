from app.db import database_proxy as db
from app.modules.db.models import AlertComment


def upgrade():
    db.create_tables([AlertComment], safe=True)


def downgrade():
    db.drop_tables([AlertComment], safe=True)
