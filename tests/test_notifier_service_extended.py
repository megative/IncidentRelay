from app.modules.db.models import AlertEvent, AlertNotification
from app.services.notifier import (
    channel_matches_alert_severity,
    format_alert_message,
    get_channel_notify_on_severities,
    has_matching_notification_channel,
    notify_alert,
    update_alert_messages,
)
from tests.factories import (
    attach_channel,
    create_alert,
    create_channel,
    create_group,
    create_route,
    create_team,
)


class FakeNotifier:
    def __init__(self, *, supports_update=False, fail_send=False, fail_update=False):
        self.supports_update = supports_update
        self.fail_send = fail_send
        self.fail_update = fail_update
        self.sent = []
        self.updated = []

    def send(self, channel, alert, text, event_type="notification"):
        if self.fail_send:
            raise RuntimeError("send failed")
        self.sent.append((channel.id, alert.id, event_type, text))
        return {
            "provider": "fake",
            "external_message_id": f"message-{alert.id}",
            "external_channel_id": f"channel-{channel.id}",
            "provider_status": "sent",
            "provider_payload": {"ok": True},
        }

    def update(self, channel, alert, text, delivery, event_type="resolved"):
        if self.fail_update:
            raise RuntimeError("update failed")
        self.updated.append((channel.id, alert.id, event_type, delivery.id))
        return {
            "provider": "fake",
            "external_message_id": delivery.external_message_id or f"message-{alert.id}",
            "external_channel_id": delivery.external_channel_id or f"channel-{channel.id}",
            "provider_status": "updated",
            "provider_payload": {"updated": True},
        }


def test_format_alert_message_contains_core_alert_fields(db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    route = create_route(team)
    alert = create_alert(route)

    message = format_alert_message(alert, event_type="notification")

    assert "NOTIFICATION: DiskFull" in message
    assert "Team: sre" in message
    assert "Status: firing" in message
    assert "Severity: critical" in message
    assert "Source: alertmanager" in message
    assert "Message: /var is 95% full" in message


def test_channel_severity_filters_are_normalized_and_legacy_key_is_supported(db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    channel = create_channel(
        group,
        team,
        config={"notify_on_severities": ["crit", "warn", "critical"]},
    )

    assert get_channel_notify_on_severities(channel) == {"critical", "warning"}

    channel.config = {"severities": "avg"}
    assert get_channel_notify_on_severities(channel) == {"medium"}


def test_invalid_channel_severity_filter_is_ignored(db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    channel = create_channel(group, team, config={"notify_on_severities": {"bad": True}})
    route = create_route(team)
    alert = create_alert(route)

    assert get_channel_notify_on_severities(channel) == set()
    assert channel_matches_alert_severity(channel, alert) is True


def test_has_matching_notification_channel_requires_route_link_and_enabled_channel(db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    route = create_route(team)
    alert = create_alert(route)
    channel = create_channel(group, team, config={"notify_on_severities": ["critical"]})
    attach_channel(route, channel)

    assert has_matching_notification_channel(alert) is True

    channel.enabled = False
    channel.save()

    assert has_matching_notification_channel(alert) is False


def test_notify_alert_sends_and_stores_delivery(monkeypatch, db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    route = create_route(team)
    channel = create_channel(group, team, channel_type="fake")
    attach_channel(route, channel)
    alert = create_alert(route)
    fake = FakeNotifier()

    monkeypatch.setattr("app.services.notifier.get_notifier", lambda channel_type: fake)

    assert notify_alert(alert, event_type="notification") == 1

    delivery = AlertNotification.get()
    assert delivery.alert == alert
    assert delivery.channel == channel
    assert delivery.provider == "fake"
    assert delivery.external_message_id == f"message-{alert.id}"
    assert delivery.external_channel_id == f"channel-{channel.id}"
    assert delivery.provider_status == "sent"
    assert delivery.provider_payload == {"ok": True}
    assert delivery.last_event_type == "notification"
    assert fake.sent[0][2] == "notification"


def test_notify_alert_skips_new_notification_when_severity_does_not_match(monkeypatch, db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    route = create_route(team)
    channel = create_channel(
        group,
        team,
        channel_type="fake",
        config={"notify_on_severities": ["warning"]},
    )
    attach_channel(route, channel)
    alert = create_alert(route)
    fake = FakeNotifier()

    monkeypatch.setattr("app.services.notifier.get_notifier", lambda channel_type: fake)

    assert notify_alert(alert, event_type="notification") == 0
    assert AlertNotification.select().count() == 0
    assert fake.sent == []


def test_notify_alert_updates_existing_editable_delivery_even_if_severity_filter_changed(monkeypatch, db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    route = create_route(team)
    channel = create_channel(
        group,
        team,
        channel_type="fake",
        config={"notify_on_severities": ["warning"]},
    )
    attach_channel(route, channel)
    alert = create_alert(route)

    delivery = AlertNotification.create(
        alert=alert,
        channel=channel,
        provider="fake",
        external_message_id="old-message",
        external_channel_id="old-channel",
        last_event_type="notification",
    )
    fake = FakeNotifier(supports_update=True)

    monkeypatch.setattr("app.services.notifier.get_notifier", lambda channel_type: fake)

    assert notify_alert(alert, event_type="acknowledged") == 1

    stored = AlertNotification.get_by_id(delivery.id)
    assert stored.last_event_type == "acknowledged"
    assert stored.provider_status == "updated"
    assert fake.updated == [(channel.id, alert.id, "acknowledged", delivery.id)]


def test_notify_alert_records_delivery_error_and_alert_event(monkeypatch, db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    route = create_route(team)
    channel = create_channel(group, team, channel_type="fake")
    attach_channel(route, channel)
    alert = create_alert(route)
    fake = FakeNotifier(fail_send=True)

    monkeypatch.setattr("app.services.notifier.get_notifier", lambda channel_type: fake)

    assert notify_alert(alert, event_type="notification") == 0

    delivery = AlertNotification.get()
    assert delivery.last_error == "send failed"
    assert AlertEvent.select().where(
        (AlertEvent.alert == alert.id) & (AlertEvent.event_type == "notification_failed")
    ).exists()


def test_update_alert_messages_updates_existing_delivery(monkeypatch, db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    route = create_route(team)
    channel = create_channel(group, team, channel_type="fake")
    attach_channel(route, channel)
    alert = create_alert(route)

    delivery = AlertNotification.create(
        alert=alert,
        channel=channel,
        provider="fake",
        external_message_id="message-1",
        external_channel_id="channel-1",
        last_event_type="notification",
    )
    fake = FakeNotifier(supports_update=True)

    monkeypatch.setattr("app.services.notifier.get_notifier", lambda channel_type: fake)

    assert update_alert_messages(alert, "resolved") == 1

    stored = AlertNotification.get_by_id(delivery.id)
    assert stored.last_event_type == "resolved"
    assert stored.provider_status == "updated"
    assert fake.updated == [(channel.id, alert.id, "resolved", delivery.id)]
