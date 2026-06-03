from datetime import datetime, timedelta

from app.modules.db.models import (
    Alert,
    UserNotificationDelivery,
    UserNotificationRule,
)
from app.services import notification_rules
from tests.factories import (
    create_alert,
    create_group,
    create_route,
    create_team,
    create_user,
)


def create_assigned_alert(user, *, status="firing", severity="critical"):
    group = create_group()
    team = create_team(group)
    route = create_route(team)

    alert = create_alert(route, status=status)
    alert.assignee = user
    alert.severity = severity
    alert.save()

    return alert


def test_create_user_notification_rule(db):
    group = create_group()
    user = create_user("alice", group)

    rule = notification_rules.create_user_rule(
        user,
        method="browser_push",
        delay_seconds=120,
        severities=["critical"],
        event_types=["notification"],
        enabled=True,
    )

    assert rule.id
    assert rule.user_id == user.id
    assert rule.method == "browser_push"
    assert rule.delay_seconds == 120
    assert rule.severities == ["critical"]
    assert rule.event_types == ["notification"]
    assert rule.position == 1
    assert rule.enabled is True


def test_list_matching_rules_filters_by_event_type_and_severity(db):
    group = create_group()
    user = create_user("alice", group)
    alert = create_assigned_alert(user, severity="critical")

    matching = notification_rules.create_user_rule(
        user,
        method="browser_push",
        delay_seconds=0,
        severities=["critical"],
        event_types=["notification"],
    )

    notification_rules.create_user_rule(
        user,
        method="email",
        delay_seconds=60,
        severities=["warning"],
        event_types=["notification"],
    )

    notification_rules.create_user_rule(
        user,
        method="voice_call",
        delay_seconds=300,
        severities=["critical"],
        event_types=["resolved"],
    )

    rules = notification_rules.list_matching_rules(alert, "notification")

    assert [rule.id for rule in rules] == [matching.id]


def test_has_deliverable_user_notification_uses_default_browser_push_without_custom_rules(
    db,
    monkeypatch,
):
    group = create_group()
    user = create_user("alice", group)
    alert = create_assigned_alert(user)

    monkeypatch.setattr(
        notification_rules.browser_push,
        "can_send_alert_push",
        lambda pushed_alert: pushed_alert.id == alert.id,
    )

    assert notification_rules.has_deliverable_user_notification(alert) is True


def test_has_deliverable_user_notification_uses_custom_rules_when_present(
    db,
    monkeypatch,
):
    group = create_group()
    user = create_user("alice", group)
    alert = create_assigned_alert(user)

    notification_rules.create_user_rule(
        user,
        method="email",
        delay_seconds=60,
        severities=["critical"],
        event_types=["notification"],
    )

    monkeypatch.setattr(
        notification_rules.browser_push,
        "can_send_alert_push",
        lambda pushed_alert: False,
    )

    assert notification_rules.has_deliverable_user_notification(alert) is True
    assert notification_rules.has_deliverable_user_notification(
        alert,
        event_type="resolved",
    ) is False


def test_enqueue_user_notifications_default_browser_push_sends_immediately(
    db,
    monkeypatch,
):
    group = create_group()
    user = create_user("alice", group)
    alert = create_assigned_alert(user)

    calls = []

    monkeypatch.setattr(
        notification_rules.browser_push,
        "can_send_alert_push",
        lambda pushed_alert: True,
    )

    def fake_send_alert_push_to_user(assignee, pushed_alert, event_type="notification"):
        calls.append(
            {
                "user_id": assignee.id,
                "alert_id": pushed_alert.id,
                "event_type": event_type,
            }
        )
        return 1

    monkeypatch.setattr(
        notification_rules.browser_push,
        "send_alert_push_to_user",
        fake_send_alert_push_to_user,
    )

    sent = notification_rules.enqueue_user_notifications(
        alert,
        event_type="notification",
    )

    assert sent == 1
    assert calls == [
        {
            "user_id": user.id,
            "alert_id": alert.id,
            "event_type": "notification",
        }
    ]

    delivery = UserNotificationDelivery.get(
        UserNotificationDelivery.alert == alert.id
    )

    assert delivery.rule_id is None
    assert delivery.method == "browser_push"
    assert delivery.status == "sent"
    assert delivery.sent_at is not None


def test_enqueue_user_notifications_creates_pending_delayed_rule(db, monkeypatch):
    group = create_group()
    user = create_user("alice", group)
    alert = create_assigned_alert(user)

    rule = notification_rules.create_user_rule(
        user,
        method="browser_push",
        delay_seconds=300,
        severities=["critical"],
        event_types=["notification"],
    )

    monkeypatch.setattr(
        notification_rules.browser_push,
        "send_alert_push_to_user",
        lambda *args, **kwargs: 1,
    )

    sent = notification_rules.enqueue_user_notifications(
        alert,
        event_type="notification",
    )

    assert sent == 0

    delivery = UserNotificationDelivery.get(
        UserNotificationDelivery.alert == alert.id
    )

    assert delivery.rule_id == rule.id
    assert delivery.method == "browser_push"
    assert delivery.status == "pending"
    assert delivery.scheduled_at > datetime.utcnow()


def test_process_due_user_notifications_sends_due_delivery(db, monkeypatch):
    group = create_group()
    user = create_user("alice", group)
    alert = create_assigned_alert(user)

    rule = notification_rules.create_user_rule(
        user,
        method="browser_push",
        delay_seconds=60,
        severities=["critical"],
        event_types=["notification"],
    )

    delivery = UserNotificationDelivery.create(
        alert=alert.id,
        user=user.id,
        rule=rule.id,
        method="browser_push",
        event_type="notification",
        status="pending",
        scheduled_at=datetime.utcnow() - timedelta(seconds=1),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    calls = []

    def fake_send_alert_push_to_user(assignee, pushed_alert, event_type="notification"):
        calls.append((assignee.id, pushed_alert.id, event_type))
        return 1

    monkeypatch.setattr(
        notification_rules.browser_push,
        "send_alert_push_to_user",
        fake_send_alert_push_to_user,
    )

    sent = notification_rules.process_due_user_notifications()

    assert sent == 1
    assert calls == [(user.id, alert.id, "notification")]

    delivery = UserNotificationDelivery.get_by_id(delivery.id)

    assert delivery.status == "sent"
    assert delivery.sent_at is not None
    assert delivery.provider == "browser_push"
    assert delivery.provider_status == "sent"


def test_process_due_user_notifications_does_not_send_future_delivery(db, monkeypatch):
    group = create_group()
    user = create_user("alice", group)
    alert = create_assigned_alert(user)

    rule = notification_rules.create_user_rule(
        user,
        method="browser_push",
        delay_seconds=60,
    )

    UserNotificationDelivery.create(
        alert=alert.id,
        user=user.id,
        rule=rule.id,
        method="browser_push",
        event_type="notification",
        status="pending",
        scheduled_at=datetime.utcnow() + timedelta(minutes=5),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    monkeypatch.setattr(
        notification_rules.browser_push,
        "send_alert_push_to_user",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("must not send future delivery")
        ),
    )

    assert notification_rules.process_due_user_notifications() == 0


def test_process_due_user_notifications_skips_if_alert_no_longer_firing(
    db,
    monkeypatch,
):
    group = create_group()
    user = create_user("alice", group)
    alert = create_assigned_alert(user, status="acknowledged")

    rule = notification_rules.create_user_rule(
        user,
        method="browser_push",
        delay_seconds=60,
    )

    delivery = UserNotificationDelivery.create(
        alert=alert.id,
        user=user.id,
        rule=rule.id,
        method="browser_push",
        event_type="notification",
        status="pending",
        scheduled_at=datetime.utcnow() - timedelta(seconds=1),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    monkeypatch.setattr(
        notification_rules.browser_push,
        "send_alert_push_to_user",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("must not send for non-firing alert")
        ),
    )

    sent = notification_rules.process_due_user_notifications()

    assert sent == 0

    delivery = UserNotificationDelivery.get_by_id(delivery.id)

    assert delivery.status == "skipped"
    assert delivery.last_error == "alert_not_firing"


def test_process_due_user_notifications_does_not_send_already_processing_delivery_twice(
    db,
    monkeypatch,
):
    group = create_group()
    user = create_user("alice", group)
    alert = create_assigned_alert(user)

    rule = notification_rules.create_user_rule(
        user,
        method="browser_push",
        delay_seconds=60,
    )

    UserNotificationDelivery.create(
        alert=alert.id,
        user=user.id,
        rule=rule.id,
        method="browser_push",
        event_type="notification",
        status="processing",
        scheduled_at=datetime.utcnow() - timedelta(seconds=1),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    monkeypatch.setattr(
        notification_rules.browser_push,
        "send_alert_push_to_user",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("must not send already processing delivery from query")
        ),
    )

    assert notification_rules.process_due_user_notifications() == 0
