from app.services.routing import build_group_key, find_route_for_alert, is_route_active
from app.services.silences import find_active_silence
from tests.factories import create_group, create_route, create_silence, create_team


def test_is_route_active_requires_route_team_and_group_to_be_active(db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    route = create_route(team)

    assert is_route_active(route)

    team.active = False
    team.save()

    assert not is_route_active(route)


def test_find_route_for_alert_matches_source_and_matchers(db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    route = create_route(
        team,
        source="alertmanager",
        matchers={"labels": {"team": "infra"}},
    )

    alert_data = {
        "source": "alertmanager",
        "team_slug": "sre",
        "title": "DiskFull",
        "labels": {"team": "infra"},
        "dedup_key": "dedup-1",
    }

    assert find_route_for_alert(alert_data) == route


def test_find_route_for_alert_records_routing_error_when_no_route_matches(db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    create_route(
        team,
        source="alertmanager",
        matchers={"labels": {"team": "infra"}},
    )

    alert_data = {
        "source": "alertmanager",
        "team_slug": "sre",
        "title": "DiskFull",
        "labels": {"team": "database"},
        "dedup_key": "dedup-1",
    }

    assert find_route_for_alert(alert_data) is None
    assert alert_data["routing_error"] == "no enabled route matched alert labels"


def test_build_group_key_uses_route_group_by_labels(db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    route = create_route(team, group_by=["alertname", "instance"])

    key = build_group_key(
        route,
        {
            "dedup_key": "dedup-1",
            "labels": {"alertname": "DiskFull", "instance": "host1"},
        },
    )

    assert key == "alertname=DiskFull|instance=host1"


def test_find_active_silence_returns_matching_active_silence(db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    silence = create_silence(team, matchers={"labels": {"alertname": "DiskFull"}})

    found = find_active_silence(
        team.id,
        {"labels": {"alertname": "DiskFull"}, "title": "DiskFull"},
    )

    assert found == silence
