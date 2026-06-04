from app.settings import Config
from app.modules.db import alerts_repo
from app.services import alerts as alerts_service
from app.services.alerts import upsert_alert
from tests.factories import create_group, create_route, create_team


def _route(group_by=None):
    group = create_group()
    team = create_team(group)

    return create_route(
        team,
        source="webhook",
        matchers={},
        group_by=group_by or ["alertname", "severity"],
    )


def _alert(route, alertname, instance, status="firing"):
    return {
        "source": "webhook",
        "forced_route_id": route.id,
        "external_id": f"{alertname}-{instance}",
        "dedup_key": f"{alertname}:{instance}",
        "status": status,
        "title": alertname,
        "message": f"{alertname} on {instance}",
        "severity": "critical",
        "labels": {
            "alertname": alertname,
            "severity": "critical",
            "instance": instance,
        },
        "payload": {
            "source": "test",
            "instance": instance,
        },
    }


def test_new_group_schedules_notification_instead_of_sending_immediately(db, monkeypatch):
    route = _route(group_by=["alertname", "severity"])

    sent = []

    monkeypatch.setattr(Config, "ALERT_GROUP_WAIT_SECONDS", 30)
    monkeypatch.setattr(
        alerts_service,
        "notify_alert",
        lambda *args, **kwargs: sent.append((args, kwargs)),
    )

    group, created = upsert_alert(_alert(route, "DiskFull", "host1"))
    group = alerts_repo.get_alert_group(group.id)

    assert created is True
    assert sent == []
    assert group.notification_pending is True
    assert group.notification_due_at is not None
    assert group.notification_reason == "notification"
    assert group.last_notification_at is None


def test_due_group_notification_is_sent(db, monkeypatch):
    route = _route(group_by=["alertname", "severity"])

    sent = []

    monkeypatch.setattr(Config, "ALERT_GROUP_WAIT_SECONDS", 0)
    monkeypatch.setattr(
        alerts_service,
        "notify_alert",
        lambda group, event_type: sent.append((group.id, event_type)),
    )

    group, _ = upsert_alert(_alert(route, "DiskFull", "host1"))

    result = alerts_service.process_due_alert_group_notifications()

    group = alerts_repo.get_alert_group(group.id)

    assert result["sent"] == 1
    assert sent == [(group.id, "notification")]
    assert group.notification_pending is False
    assert group.notification_due_at is None
    assert group.last_notification_at is not None


def test_group_resolved_before_group_wait_does_not_send_notification(db, monkeypatch):
    route = _route(group_by=["alertname", "severity"])

    sent = []

    monkeypatch.setattr(Config, "ALERT_GROUP_WAIT_SECONDS", 60)
    monkeypatch.setattr(
        alerts_service,
        "notify_alert",
        lambda *args, **kwargs: sent.append((args, kwargs)),
    )

    group, _ = upsert_alert(_alert(route, "DiskFull", "host1"))

    upsert_alert(_alert(route, "DiskFull", "host1", status="resolved"))

    group = alerts_repo.get_alert_group(group.id)

    assert group.status == "resolved"
    assert group.notification_pending is False

    result = alerts_service.process_due_alert_group_notifications()

    assert result["sent"] == 0
    assert sent == []
