from app.modules.db import alerts_repo
from app.modules.db.models import Alert
from tests.factories import create_group, create_route, create_service, create_team


def _create_alert(team, route, service, title, status, severity, dedup_key):
    return Alert.create(
        source="test",
        team=team,
        route=route,
        service=service,
        group_key="multi-filter-b",
        dedup_key=dedup_key,
        title=title,
        message=title,
        severity=severity,
        status=status,
        labels={},
        payload={},
    )


def test_paginate_alerts_filters_by_multiple_statuses_severities_and_services(db):
    group = create_group()
    team = create_team(group)
    route = create_route(team, source="test")
    service_a = create_service(team, name="API", slug="api")
    service_b = create_service(team, name="DB", slug="db")
    service_c = create_service(team, name="Cache", slug="cache")

    keep_a = _create_alert(team, route, service_a, "critical firing api", "firing", "critical", "multi-filter-a")
    keep_b = _create_alert(team, route, service_b, "warning ack db", "acknowledged", "warning", "multi-filter-b")
    _create_alert(team, route, service_c, "critical firing cache", "firing", "critical", "multi-filter-c")
    _create_alert(team, route, service_a, "low resolved api", "resolved", "low", "multi-filter-d")

    page = alerts_repo.paginate_alerts(
        team_id=team.id,
        status=["firing", "acknowledged"],
        severity=["critical", "warning"],
        service_id=[service_a.id, service_b.id],
        sort="id",
        order="asc",
        page_size=25,
    )

    assert [alert.id for alert in page["items"]] == [keep_a.id, keep_b.id]
    assert page["pagination"]["total_items"] == 2
    assert page["summary"]["firing"] == 1
    assert page["summary"]["acknowledged"] == 1


def test_paginate_alerts_accepts_comma_separated_multi_filters(db):
    group = create_group()
    team = create_team(group)
    route = create_route(team, source="test")
    service = create_service(team, name="API", slug="api-comma")

    keep = _create_alert(team, route, service, "critical firing api", "firing", "critical", "multi-filter-comma-a")
    _create_alert(team, route, service, "low resolved api", "resolved", "low", "multi-filter-comma-b")

    page = alerts_repo.paginate_alerts(
        team_id=team.id,
        status="firing,acknowledged",
        severity="critical,warning",
        service_id=str(service.id),
        sort="id",
        order="asc",
    )

    assert [alert.id for alert in page["items"]] == [keep.id]
