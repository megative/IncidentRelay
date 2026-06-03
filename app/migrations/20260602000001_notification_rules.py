from app.db import database_proxy as db
from app.modules.db.models import (
    AlertRouteChannel,
    NotificationChannel,
    UserNotificationDelivery,
    UserNotificationRule,
)


def upgrade():
    db.create_tables(
        [
            UserNotificationRule,
            UserNotificationDelivery,
        ],
        safe=True,
    )

    voice_channels = (
        NotificationChannel
        .select(NotificationChannel.id)
        .where(NotificationChannel.channel_type == "voice_call")
    )

    (
        AlertRouteChannel
        .delete()
        .where(AlertRouteChannel.channel.in_(voice_channels))
        .execute()
    )

    (
        NotificationChannel
        .delete()
        .where(NotificationChannel.channel_type == "voice_call")
        .execute()
    )


def downgrade():
    db.drop_tables(
        [
            UserNotificationDelivery,
            UserNotificationRule,
        ],
        safe=True,
    )
