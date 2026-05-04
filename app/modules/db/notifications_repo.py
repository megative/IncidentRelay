from datetime import datetime

from app.modules.db.models import AlertNotification, AlertNotificationEvent


def get_notification(alert_id, channel_id):
    """Return a delivery record for an alert/channel pair."""

    return AlertNotification.get_or_none(
        (AlertNotification.alert == alert_id)
        & (AlertNotification.channel == channel_id)
    )


def get_notification_by_external_id(channel_id, external_message_id):
    """Return a delivery record by provider call/message id."""

    if not external_message_id:
        return None

    return AlertNotification.get_or_none(
        (AlertNotification.channel == channel_id)
        & (AlertNotification.external_message_id == external_message_id)
    )


def save_notification(
    alert_id,
    channel_id,
    provider,
    external_message_id=None,
    external_channel_id=None,
    event_type=None,
    error=None,
    provider_status=None,
    provider_payload=None,
):
    """Create or update a delivery record."""

    record = get_notification(alert_id, channel_id)

    if not record:
        record = AlertNotification.create(
            alert=alert_id,
            channel=channel_id,
            provider=provider,
            external_message_id=external_message_id,
            external_channel_id=external_channel_id,
            last_event_type=event_type,
            last_error=error,
            provider_status=provider_status,
            provider_payload=provider_payload,
            updated_at=datetime.utcnow(),
        )
        return record

    record.provider = provider or record.provider
    record.external_message_id = external_message_id or record.external_message_id
    record.external_channel_id = external_channel_id or record.external_channel_id
    record.last_event_type = event_type or record.last_event_type
    record.last_error = error
    record.provider_status = provider_status or record.provider_status

    if provider_payload is not None:
        record.provider_payload = provider_payload

    record.updated_at = datetime.utcnow()
    record.save()

    return record


def update_notification_callback_state(
    notification,
    event_type,
    provider_status=None,
    provider_payload=None,
):
    """Update notification state after provider callback."""

    notification.last_event_type = event_type or notification.last_event_type
    notification.provider_status = provider_status or notification.provider_status

    if provider_payload is not None:
        notification.provider_payload = provider_payload

    notification.last_callback_at = datetime.utcnow()
    notification.callback_count = (notification.callback_count or 0) + 1
    notification.updated_at = datetime.utcnow()
    notification.save()

    return notification


def create_notification_event(
    notification,
    event_type,
    provider_status=None,
    digit=None,
    action=None,
    message=None,
    payload=None,
):
    """Create provider callback history event."""

    return AlertNotificationEvent.create(
        notification=notification.id,
        event_type=event_type,
        provider_status=provider_status,
        digit=digit,
        action=action,
        message=message,
        payload=payload,
    )


def mark_notification_error(alert_id, channel_id, provider, event_type, error):
    """Store the latest delivery error for an alert/channel pair."""

    return save_notification(
        alert_id=alert_id,
        channel_id=channel_id,
        provider=provider,
        event_type=event_type,
        error=str(error),
    )


def list_notifications_for_alert(alert_id):
    """Return delivery records for an alert ordered by id."""

    return list(
        AlertNotification.select()
        .where(AlertNotification.alert == alert_id)
        .order_by(AlertNotification.id.asc())
    )
