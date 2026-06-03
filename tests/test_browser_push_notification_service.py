from datetime import datetime

from app.modules.db.models import Alert, AlertEvent, BrowserPushSubscription
from app.services import notification_service
from tests.factories import (
    attach_channel,
    create_alert,
    create_channel,
    create_group,
    create_route,
    create_team,
    create_user,
)


def create_push_subscription(user):
    now = datetime.utcnow()

    return BrowserPushSubscription.create(
        user=user.id,
        endpoint=f"https://push.example.test/{user.id}",
        p256dh="test-p256dh",
        auth="test-auth",
        device_name="Test browser",
        user_agent="pytest",
        enabled=True,
        deleted=False,
        created_at=now,
        updated_at=now,
        last_seen_at=now,
    )


def create_assigned_alert(user, *, with_regular_channel=False):
    group = create_group()
    team = create_team(group)
    route = create_route(team)

    if with_regular_channel:
        channel = create_channel(
            group,
            team,
            channel_type="webhook",
            config={"webhook_url": "https://webhook.example.test"},
        )
        attach_channel(route, channel)

    alert = create_alert(route)
    alert.assignee = user
    alert.save()

    return alert


def test_has_matching_notification_channel_returns_true_for_active_push_subscription(db, monkeypatch):
    monkeypatch.setattr(
        notification_service.browser_push.Config,
        "BROWSER_PUSH_ENABLED",
        True,
        raising=False,
    )

    group = create_group()
    user = create_user("alice", group)
    alert = create_assigned_alert(user)

    create_push_subscription(user)

    assert notification_service.has_matching_notification_channel(alert) is True


def test_has_matching_notification_channel_returns_false_without_channels_or_push(db, monkeypatch):
    monkeypatch.setattr(
        notification_service.browser_push.Config,
        "BROWSER_PUSH_ENABLED",
        True,
        raising=False,
    )

    group = create_group()
    user = create_user("alice", group)
    alert = create_assigned_alert(user)

    assert notification_service.has_matching_notification_channel(alert) is False


def test_notify_alert_sends_profile_browser_push_without_route_channels(db, monkeypatch):
    group = create_group()
    user = create_user("alice", group)
    alert = create_assigned_alert(user)

    calls = []

    def fake_send_alert_push_to_user(assignee, pushed_alert, event_type="notification"):
        calls.append(
            {
                "assignee_id": assignee.id,
                "alert_id": pushed_alert.id,
                "event_type": event_type,
            }
        )
        return 1

    monkeypatch.setattr(
        notification_service.browser_push,
        "send_alert_push_to_user",
        fake_send_alert_push_to_user,
    )

    sent = notification_service.notify_alert(alert, event_type="notification")

    assert sent == 1
    assert calls == [
        {
            "assignee_id": user.id,
            "alert_id": alert.id,
            "event_type": "notification",
        }
    ]

    alert = Alert.get_by_id(alert.id)

    assert alert.last_notification_at is not None

    event = AlertEvent.get(
        (AlertEvent.alert == alert.id)
        & (AlertEvent.event_type == "notification_browser_push_sent")
    )

    assert "Sent browser push" in event.message


def test_notify_alert_does_not_send_browser_push_without_assignee(db, monkeypatch):
    group = create_group()
    team = create_team(group)
    route = create_route(team)
    alert = create_alert(route)

    calls = []

    def fake_send_alert_push_to_user(assignee, pushed_alert, event_type="notification"):
        calls.append((assignee, pushed_alert, event_type))
        return 1

    monkeypatch.setattr(
        notification_service.browser_push,
        "send_alert_push_to_user",
        fake_send_alert_push_to_user,
    )

    sent = notification_service.notify_alert(alert, event_type="notification")

    assert sent == 0
    assert calls == []


def test_notify_alert_counts_regular_channel_and_browser_push(db, monkeypatch):
    group = create_group()
    user = create_user("alice", group)
    alert = create_assigned_alert(user, with_regular_channel=True)

    class FakeNotifier:
        supports_update = False

        def send(self, channel, alert, text, event_type="notification"):
            return {
                "provider": "webhook",
                "provider_status": "sent",
                "external_message_id": "msg-1",
                "provider_payload": {},
            }

    monkeypatch.setattr(
        notification_service,
        "get_notifier",
        lambda channel_type: FakeNotifier(),
    )

    monkeypatch.setattr(
        notification_service.browser_push,
        "send_alert_push_to_user",
        lambda assignee, alert, event_type="notification": 1,
    )

    sent = notification_service.notify_alert(alert, event_type="notification")

    assert sent == 2

    event_types = {
        row.event_type
        for row in AlertEvent.select().where(AlertEvent.alert == alert.id)
    }

    assert "notification_sent" in event_types
    assert "notification_browser_push_sent" in event_types
