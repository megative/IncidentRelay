from datetime import datetime, timedelta

from app.modules.db import alerts_repo, escalation_policies_repo
from app.modules.db.models import Alert, AlertEvent, AlertGroup
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
    create_group,
    create_route,
    create_rotation,
    create_silence,
    create_team,
    create_user,
)


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
            "severity": "critical",
            "instance": "host1",
            "team": "sre",
        },
        "payload": {"source": "test"},
        "status": "firing",
    }
    data.update(overrides)
    return data


def create_alert_group_for_route(route, **overrides):
    data = normalized_alert(
        forced_route_id=route.id,
        team_slug=None,
    )
    data.update(overrides)

    alert_group, _ = upsert_alert(data)

    assert alert_group is not None

    return alert_group


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
        lambda alert_group, event_type="notification": calls.append((alert_group.id, event_type)) or 1,
    )

    alert_group, created = upsert_alert(normalized_alert())

    assert created is True
    assert alert_group.team == team
    assert alert_group.route == route
    assert alert_group.rotation == rotation
    assert alert_group.assignee == user
    assert alert_group.group_key == (
        f"source=alertmanager|team_id={route.team_id}|"
        f"route_id={route.id}|service_id=|"
        "alertname=DiskFull|severity=critical"
    )
    assert alert_group.status == "firing"

    child = alerts_repo.list_alerts_for_group(alert_group.id)[0]

    assert child.dedup_key == "dedup-1"
    assert child.team == team
    assert child.route == route
    assert child.rotation == rotation
    assert child.assignee == user

    assert calls == []

    assert AlertEvent.select().where(
        (AlertEvent.group == alert_group.id)
        & (AlertEvent.event_type == "created")
    ).exists()


def test_upsert_alert_ignores_orphan_resolved_payload(monkeypatch, db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")

    create_route(team)

    monkeypatch.setattr(
        "app.services.alerts.notify_alert",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not notify")),
    )

    alert_group, created = upsert_alert(normalized_alert(status="resolved"))

    assert alert_group is None
    assert created is False
    assert Alert.select().count() == 0
    assert AlertGroup.select().count() == 0


def test_upsert_alert_preserves_acknowledged_status_when_payload_fires_again(db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")

    create_route(team)

    alert_group, created = upsert_alert(normalized_alert())

    assert created is True

    alerts_repo.acknowledge_alert_group(alert_group.id)

    alert_group, created = upsert_alert(normalized_alert(message="updated message"))

    assert created is False
    assert alert_group.status == "acknowledged"
    assert alert_group.message == "updated message"

    child = alerts_repo.list_alerts_for_group(alert_group.id)[0]

    assert child.status == "firing"
    assert child.message == "updated message"

    assert AlertEvent.select().where(
        (AlertEvent.group == alert_group.id)
        & (AlertEvent.event_type == "updated")
    ).exists()


def test_upsert_alert_resolves_existing_alert_and_notifies(monkeypatch, db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")

    create_route(team)

    alert_group, created = upsert_alert(normalized_alert())

    assert created is True

    alert_group.last_notification_at = datetime.utcnow()
    alert_group.save()

    calls = []

    monkeypatch.setattr(
        "app.services.alerts.notify_alert",
        lambda alert_group, event_type="notification": calls.append(event_type) or 1,
    )

    alert_group, created = upsert_alert(normalized_alert(status="resolved"))

    assert created is False
    assert alert_group.status == "resolved"
    assert alert_group.resolved_at is not None

    child = alerts_repo.list_alerts_for_group(alert_group.id)[0]

    assert child.status == "resolved"
    assert child.resolved_at is not None
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

    alert_group, created = upsert_alert(normalized_alert())

    assert created is True
    assert alert_group.status == "silenced"
    assert alert_group.silenced is True

    child = alerts_repo.list_alerts_for_group(alert_group.id)[0]

    assert child.status == "silenced"
    assert child.silenced is True

    assert AlertEvent.select().where(
        (AlertEvent.group == alert_group.id)
        & (AlertEvent.event_type == "silenced")
        & (AlertEvent.message.contains(silence.name))
    ).exists()


def test_acknowledge_and_resolve_alert_update_statuses_and_create_events(monkeypatch, db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    user = create_user("alice", group)

    create_route(team)

    alert_group, created = upsert_alert(normalized_alert())

    assert created is True

    updates = []

    monkeypatch.setattr(
        "app.services.alerts.update_alert_messages",
        lambda alert_group, event_type: updates.append((alert_group.id, event_type)) or 1,
    )

    acknowledged = acknowledge_alert(alert_group.id, user_id=user.id)
    resolved = resolve_alert(alert_group.id, user_id=user.id)

    assert acknowledged.status == "acknowledged"
    assert acknowledged.acknowledged_by == user
    assert acknowledged.acknowledged_at is not None

    assert resolved.status == "resolved"
    assert resolved.resolved_at is not None

    assert updates == [
        (alert_group.id, "acknowledged"),
        (alert_group.id, "resolved"),
    ]

    assert [
        event.event_type
        for event in (
            AlertEvent
            .select()
            .where(
                (AlertEvent.group == alert_group.id)
                & (AlertEvent.event_type.in_(["acknowledged", "resolved"]))
            )
            .order_by(AlertEvent.id.asc())
        )
    ] == ["acknowledged", "resolved"]


def test_reminder_interval_uses_rotation_before_global_config(db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    rotation = create_rotation(team)

    rotation.reminder_interval_seconds = 60
    rotation.save()

    route = create_route(team, rotation=rotation)
    alert_group = create_alert_group_for_route(route)

    now = datetime.utcnow()

    assert get_alert_reminder_interval(alert_group) == 60

    alert_group.last_notification_at = None
    assert should_send_reminder(alert_group, now) is True

    alert_group.last_notification_at = now - timedelta(seconds=61)
    assert should_send_reminder(alert_group, now) is True

    alert_group.last_notification_at = now - timedelta(seconds=59)
    assert should_send_reminder(alert_group, now) is False


def test_send_unacked_reminders_counts_only_successful_sends(monkeypatch, db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    rotation = create_rotation(team)
    route = create_route(team, rotation=rotation)

    alert_group = create_alert_group_for_route(route)

    alert_group.last_notification_at = None
    alert_group.save()

    monkeypatch.setattr("app.services.alerts.has_matching_notification_channel", lambda alert_group: True)
    monkeypatch.setattr("app.services.alerts.maybe_escalate_alert", lambda alert_group: False)
    monkeypatch.setattr("app.services.alerts.notify_alert", lambda alert_group, event_type="reminder": 1)

    assert send_unacked_reminders() == 1

    stored = AlertGroup.get_by_id(alert_group.id)

    assert stored.reminder_count == 1
    assert stored.last_notification_at is not None

    assert AlertEvent.select().where(
        (AlertEvent.group == alert_group.id)
        & (AlertEvent.event_type == "reminder_sent")
    ).exists()


def test_zero_reminder_interval_disables_reminders(db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    rotation = create_rotation(team)

    rotation.reminder_interval_seconds = 0
    rotation.save()

    route = create_route(team, rotation=rotation)
    alert_group = create_alert_group_for_route(route)

    alert_group.last_notification_at = None

    assert get_alert_reminder_interval(alert_group) == 0
    assert should_send_reminder(alert_group, datetime.utcnow()) is False


def test_send_unacked_reminders_does_not_increment_when_no_notification_was_sent(monkeypatch, db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    rotation = create_rotation(team)
    route = create_route(team, rotation=rotation)

    alert_group = create_alert_group_for_route(route)

    alert_group.last_notification_at = None
    alert_group.save()

    monkeypatch.setattr("app.services.alerts.has_matching_notification_channel", lambda alert_group: True)
    monkeypatch.setattr("app.services.alerts.maybe_escalate_alert", lambda alert_group: False)
    monkeypatch.setattr("app.services.alerts.notify_alert", lambda alert_group, event_type="reminder": 0)

    assert send_unacked_reminders() == 0

    stored = AlertGroup.get_by_id(alert_group.id)

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

    alert_group = create_alert_group_for_route(route)

    alert_group.assignee = first
    alert_group.reminder_count = 1
    alert_group.save()

    calls = []

    monkeypatch.setattr("app.services.alerts.has_matching_notification_channel", lambda alert_group: True)
    monkeypatch.setattr(
        "app.services.alerts.notify_alert",
        lambda alert_group, event_type="escalation": calls.append(event_type) or 1,
    )

    assert maybe_escalate_alert(alert_group) is True

    stored = AlertGroup.get_by_id(alert_group.id)

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

    alert_group, created = upsert_alert(
        {
            "source": "test",
            "dedup_key": "policy-user-position-2",
            "title": "Policy user test",
            "message": "test",
            "severity": "critical",
            "labels": {
                "alertname": "PolicyUserTest",
                "severity": "critical",
            },
            "payload": {},
            "status": "firing",
        }
    )

    assert alert_group is not None
    assert created is True
    assert alert_group.escalation_policy_id == policy.id
    assert alert_group.escalation_rule_id == rule.id
    assert alert_group.rotation_id is None
    assert alert_group.assignee_id == alice.id
    assert alert_group.next_escalation_at is not None


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

    alert_group, created = upsert_alert(
        {
            "source": "test",
            "dedup_key": "policy-rotation-position-2",
            "title": "Policy rotation test",
            "message": "test",
            "severity": "critical",
            "labels": {
                "alertname": "PolicyRotationTest",
                "severity": "critical",
            },
            "payload": {},
            "status": "firing",
        }
    )

    assert alert_group is not None
    assert created is True
    assert alert_group.escalation_policy_id == policy.id
    assert alert_group.escalation_rule_id == rule.id
    assert alert_group.rotation_id == rotation.id
    assert alert_group.assignee_id == alice.id
    assert alert_group.next_escalation_at is not None


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

    alert_group, created = upsert_alert(
        {
            "source": "test",
            "dedup_key": "policy-second-rule-rotation",
            "title": "Policy rotation test",
            "message": "test",
            "severity": "critical",
            "labels": {
                "alertname": "PolicyRotationTest",
                "severity": "critical",
            },
            "payload": {},
            "status": "firing",
        }
    )

    assert alert_group is not None
    assert created is True
    assert alert_group.escalation_policy_id == policy.id
    assert alert_group.escalation_rule_id == second_rule.id
    assert alert_group.rotation_id == rotation.id
    assert alert_group.assignee_id == alice.id
    assert alert_group.next_escalation_at is not None
