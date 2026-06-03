from datetime import datetime, timedelta

from app.modules.db.models import Alert, AlertEvent
from app.services.alerts import (
    acknowledge_alert,
    get_alert_reminder_interval,
    maybe_escalate_alert,
    resolve_alert,
    send_unacked_reminders,
    should_send_reminder,
    upsert_alert,
)
from tests.factories import (
    add_user_to_team,
    create_alert,
    create_group,
    create_route,
    create_rotation,
    create_silence,
    create_team,
    create_user,
)
from app.modules.db import escalation_policies_repo


def normalized_alert(**overrides):
    data = {
        "source": "alertmanager",
        "team_slug": "sre",
        "external_id": "external-1",
        "dedup_key": "dedup-1",
        "title": "DiskFull",
        "message": "/var is 95% full",
        "severity": "critical",
        "labels": {
            "alertname": "DiskFull",
            "instance": "host1",
            "team": "sre",
        },
        "payload": {"source": "test"},
        "status": "firing",
    }
    data.update(overrides)
    return data


def test_upsert_alert_creates_routed_alert_with_current_oncall(monkeypatch, db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    user = create_user("alice", group)
    add_user_to_team(team, user)
    rotation = create_rotation(team, users=[user])
    route = create_route(team, rotation=rotation)

    calls = []
    monkeypatch.setattr(
        "app.services.alerts.notify_alert",
        lambda alert, event_type="notification": calls.append((alert.id, event_type)) or 1,
    )

    alert, created = upsert_alert(normalized_alert())

    assert created is True
    assert alert.team == team
    assert alert.route == route
    assert alert.rotation == rotation
    assert alert.assignee == user
    assert alert.group_key == "dedup-1"
    assert alert.status == "firing"
    assert calls == [(alert.id, "notification")]
    assert AlertEvent.select().where(
        (AlertEvent.alert == alert.id) & (AlertEvent.event_type == "created")
    ).exists()


def test_upsert_alert_ignores_orphan_resolved_payload(monkeypatch, db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    create_route(team)

    monkeypatch.setattr(
        "app.services.alerts.notify_alert",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not notify")),
    )

    alert, created = upsert_alert(normalized_alert(status="resolved"))

    assert alert is None
    assert created is False
    assert Alert.select().count() == 0


def test_upsert_alert_preserves_acknowledged_status_when_payload_fires_again(db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    route = create_route(team)
    existing = create_alert(route, status="acknowledged")
    existing.source = "alertmanager"
    existing.dedup_key = "dedup-1"
    existing.save()

    alert, created = upsert_alert(normalized_alert(message="updated message"))

    assert created is False
    assert alert.id == existing.id
    assert alert.status == "acknowledged"
    assert alert.previous_status == "acknowledged"
    assert alert.message == "updated message"
    assert AlertEvent.select().where(
        (AlertEvent.alert == alert.id) & (AlertEvent.event_type == "updated")
    ).exists()


def test_upsert_alert_resolves_existing_alert_and_notifies(monkeypatch, db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    route = create_route(team)
    existing = create_alert(route)
    existing.source = "alertmanager"
    existing.dedup_key = "dedup-1"
    existing.save()

    calls = []
    monkeypatch.setattr(
        "app.services.alerts.notify_alert",
        lambda alert, event_type="notification": calls.append(event_type) or 1,
    )

    alert, created = upsert_alert(normalized_alert(status="resolved"))

    assert created is False
    assert alert.id == existing.id
    assert alert.status == "resolved"
    assert alert.resolved_at is not None
    assert calls == ["resolved"]


def test_upsert_alert_creates_silenced_alert_without_notification(monkeypatch, db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    create_route(team)
    silence = create_silence(team, matchers={"labels": {"alertname": "DiskFull"}})

    monkeypatch.setattr(
        "app.services.alerts.notify_alert",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not notify")),
    )

    alert, created = upsert_alert(normalized_alert())

    assert created is True
    assert alert.status == "silenced"
    assert alert.silenced is True
    assert AlertEvent.select().where(
        (AlertEvent.alert == alert.id)
        & (AlertEvent.event_type == "silenced")
        & (AlertEvent.message.contains(silence.name))
    ).exists()


def test_acknowledge_and_resolve_alert_update_statuses_and_create_events(monkeypatch, db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    user = create_user("alice", group)
    route = create_route(team)
    alert = create_alert(route)

    updates = []
    monkeypatch.setattr(
        "app.services.alerts.update_alert_messages",
        lambda alert, event_type: updates.append((alert.id, event_type)) or 1,
    )

    acknowledged = acknowledge_alert(alert.id, user_id=user.id)
    resolved = resolve_alert(alert.id, user_id=user.id)

    assert acknowledged.status == "acknowledged"
    assert acknowledged.acknowledged_by == user
    assert acknowledged.acknowledged_at is not None
    assert resolved.status == "resolved"
    assert resolved.resolved_at is not None
    assert updates == [(alert.id, "acknowledged"), (alert.id, "resolved")]
    assert [
        event.event_type
        for event in AlertEvent.select()
        .where(AlertEvent.alert == alert.id)
        .order_by(AlertEvent.id.asc())
    ] == ["acknowledged", "resolved"]


def test_reminder_interval_uses_rotation_before_global_config(db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    rotation = create_rotation(team)
    rotation.reminder_interval_seconds = 60
    rotation.save()
    route = create_route(team, rotation=rotation)
    alert = create_alert(route)
    now = datetime.utcnow()

    assert get_alert_reminder_interval(alert) == 60

    alert.last_notification_at = None
    assert should_send_reminder(alert, now) is True

    alert.last_notification_at = now - timedelta(seconds=61)
    assert should_send_reminder(alert, now) is True

    alert.last_notification_at = now - timedelta(seconds=59)
    assert should_send_reminder(alert, now) is False


def test_send_unacked_reminders_counts_only_successful_sends(monkeypatch, db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    rotation = create_rotation(team)
    route = create_route(team, rotation=rotation)
    alert = create_alert(route)
    alert.last_notification_at = None
    alert.save()

    monkeypatch.setattr("app.services.alerts.has_matching_notification_channel", lambda alert: True)
    monkeypatch.setattr("app.services.alerts.maybe_escalate_alert", lambda alert: False)
    monkeypatch.setattr("app.services.alerts.notify_alert", lambda alert, event_type="reminder": 1)

    assert send_unacked_reminders() == 1

    stored = Alert.get_by_id(alert.id)
    assert stored.reminder_count == 1
    assert stored.last_notification_at is not None
    assert AlertEvent.select().where(
        (AlertEvent.alert == alert.id) & (AlertEvent.event_type == "reminder_sent")
    ).exists()


def test_zero_reminder_interval_disables_reminders(db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    rotation = create_rotation(team)
    rotation.reminder_interval_seconds = 0
    rotation.save()

    route = create_route(team, rotation=rotation)
    alert = create_alert(route)
    alert.last_notification_at = None

    assert get_alert_reminder_interval(alert) == 0
    assert should_send_reminder(alert, datetime.utcnow()) is False


def test_send_unacked_reminders_does_not_increment_when_no_notification_was_sent(monkeypatch, db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    rotation = create_rotation(team)
    route = create_route(team, rotation=rotation)
    alert = create_alert(route)
    alert.last_notification_at = None
    alert.save()

    monkeypatch.setattr("app.services.alerts.has_matching_notification_channel", lambda alert: True)
    monkeypatch.setattr("app.services.alerts.maybe_escalate_alert", lambda alert: False)
    monkeypatch.setattr("app.services.alerts.notify_alert", lambda alert, event_type="reminder": 0)

    assert send_unacked_reminders() == 0

    stored = Alert.get_by_id(alert.id)
    assert stored.reminder_count == 0


def test_maybe_escalate_alert_assigns_next_rotation_user(monkeypatch, db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    team.escalation_after_reminders = 0
    team.save()

    first = create_user("alice", group)
    second = create_user("bob", group)
    add_user_to_team(team, first)
    add_user_to_team(team, second)
    rotation = create_rotation(team, users=[first, second])
    route = create_route(team, rotation=rotation)
    alert = create_alert(route)
    alert.assignee = first
    alert.reminder_count = 1
    alert.save()

    calls = []
    monkeypatch.setattr("app.services.alerts.has_matching_notification_channel", lambda alert: True)
    monkeypatch.setattr(
        "app.services.alerts.notify_alert",
        lambda alert, event_type="escalation": calls.append(event_type) or 1,
    )

    assert maybe_escalate_alert(alert) is True

    stored = Alert.get_by_id(alert.id)
    assert stored.assignee == second
    assert stored.escalation_level == 1
    assert stored.reminder_count == 0
    assert calls == ["escalation"]


def test_policy_alert_assigns_user_when_first_enabled_rule_position_is_not_one(db):
    group = create_group()
    team = create_team(group)
    route = create_route(team, source="test")

    alice = create_user(group=group)
    add_user_to_team(team, alice)

    policy = escalation_policies_repo.create_policy(
        team_id=team.id,
        name="Default policy",
        enabled=True,
        repeat_count=0,
    )

    rule = escalation_policies_repo.create_rule(
        policy_id=policy.id,
        position=2,
        delay_seconds=300,
        target_type="user",
        target_id=alice.id,
        enabled=True,
    )

    route.escalation_policy = policy
    route.save()

    alert, created = upsert_alert(
        {
            "source": "test",
            "dedup_key": "policy-user-position-2",
            "title": "Policy user test",
            "message": "test",
            "severity": "critical",
            "labels": {
                "alertname": "PolicyUserTest",
            },
            "payload": {},
            "status": "firing",
        }
    )

    assert alert is not None
    assert created is True
    assert alert.escalation_policy_id == policy.id
    assert alert.escalation_rule_id == rule.id
    assert alert.rotation_id is None
    assert alert.assignee_id == alice.id
    assert alert.next_escalation_at is not None


def test_policy_alert_assigns_rotation_when_first_enabled_rule_position_is_not_one(db):
    group = create_group()
    team = create_team(group)
    route = create_route(team, source="test")

    alice = create_user(group=group)
    add_user_to_team(team, alice)

    rotation = create_rotation(
        team,
        users=[alice],
        duration_seconds=86400,
    )

    policy = escalation_policies_repo.create_policy(
        team_id=team.id,
        name="Default policy",
        enabled=True,
        repeat_count=0,
    )

    rule = escalation_policies_repo.create_rule(
        policy_id=policy.id,
        position=2,
        delay_seconds=300,
        target_type="rotation",
        target_id=rotation.id,
        enabled=True,
    )

    route.escalation_policy = policy
    route.save()

    alert, created = upsert_alert(
        {
            "source": "test",
            "dedup_key": "policy-rotation-position-2",
            "title": "Policy rotation test",
            "message": "test",
            "severity": "critical",
            "labels": {
                "alertname": "PolicyRotationTest",
            },
            "payload": {},
            "status": "firing",
        }
    )

    assert alert is not None
    assert created is True
    assert alert.escalation_policy_id == policy.id
    assert alert.escalation_rule_id == rule.id
    assert alert.rotation_id == rotation.id
    assert alert.assignee_id == alice.id
    assert alert.next_escalation_at is not None


def test_policy_alert_assigns_rotation_when_first_rule_was_deleted_and_second_is_rotation(db):
    group = create_group()
    team = create_team(group)
    route = create_route(team, source="test")

    alice = create_user(group=group)
    add_user_to_team(team, alice)

    rotation = create_rotation(
        team,
        users=[alice],
        duration_seconds=86400,
    )

    policy = escalation_policies_repo.create_policy(
        team_id=team.id,
        name="Default policy",
        enabled=True,
        repeat_count=0,
    )

    first_rule = escalation_policies_repo.create_rule(
        policy_id=policy.id,
        position=1,
        delay_seconds=60,
        target_type="rotation",
        target_id=rotation.id,
        enabled=True,
    )

    second_rule = escalation_policies_repo.create_rule(
        policy_id=policy.id,
        position=2,
        delay_seconds=300,
        target_type="rotation",
        target_id=rotation.id,
        enabled=True,
    )

    escalation_policies_repo.delete_rule(first_rule.id)

    route.escalation_policy = policy
    route.save()

    alert, created = upsert_alert(
        {
            "source": "test",
            "dedup_key": "policy-second-rule-rotation",
            "title": "Policy rotation test",
            "message": "test",
            "severity": "critical",
            "labels": {
                "alertname": "PolicyRotationTest",
            },
            "payload": {},
            "status": "firing",
        }
    )

    assert alert is not None
    assert created is True
    assert alert.escalation_policy_id == policy.id
    assert alert.escalation_rule_id == second_rule.id
    assert alert.rotation_id == rotation.id
    assert alert.assignee_id == alice.id
    assert alert.next_escalation_at is not None
