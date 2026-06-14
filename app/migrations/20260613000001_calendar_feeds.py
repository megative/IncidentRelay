"""Add tokenized ICS calendar feeds."""

from app.db import init_database
from app.modules.db.models import CalendarFeed


db = init_database()


def upgrade():
    db.create_tables([CalendarFeed], safe=True)


def downgrade():
    db.drop_tables([CalendarFeed], safe=True)
