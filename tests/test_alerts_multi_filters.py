from app.modules.db import alerts_repo
from app.services.alerts import upsert_alert
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


def _route(group_by=None):
    group = create_group()
    team = create_team(group)

    return create_route(
        team,
        source="webhook",
        matchers={},
        group_by=group_by or ["alertname", "severity"],
    )


def _alert(route, alertname, instance, status="firing", severity="critical"):
    return {
        "source": "webhook",
        "forced_route_id": route.id,
        "external_id": f"{alertname}-{instance}",
        "dedup_key": f"{alertname}:{instance}",
        "status": status,
        "title": alertname,
        "message": f"{alertname} on {instance}",
        "severity": severity,
        "labels": {
            "alertname": alertname,
            "severity": severity,
            "instance": instance,
        },
        "payload": {
            "source": "test",
            "instance": instance,
        },
    }


def test_alerts_api_accepts_multiple_status_filters(client, admin_headers, db):
    route = _route(group_by=["alertname", "severity", "instance"])

    firing_group, _ = upsert_alert(_alert(route, "DiskFull", "host1"))
    acknowledged_group, _ = upsert_alert(_alert(route, "DiskFull", "host2"))
    resolved_group, _ = upsert_alert(_alert(route, "DiskFull", "host3"))

    alerts_repo.acknowledge_alert_group(acknowledged_group.id)
    alerts_repo.resolve_alert_group(resolved_group.id)

    response = client.get(
        "/api/alerts?status=firing&status=acknowledged&sort=id&order=asc",
        headers=admin_headers,
    )

    assert response.status_code == 200

    payload = response.get_json()
    ids = {item["id"] for item in payload["items"]}

    assert firing_group.id in ids
    assert acknowledged_group.id in ids
    assert resolved_group.id not in ids


def test_alerts_api_accepts_multiple_severity_filters(client, admin_headers, db):
    route = _route(group_by=["alertname", "severity", "instance"])

    critical_group, _ = upsert_alert(
        _alert(route, "DiskFull", "host1", severity="critical")
    )
    warning_group, _ = upsert_alert(
        _alert(route, "DiskFull", "host2", severity="warning")
    )
    info_group, _ = upsert_alert(
        _alert(route, "DiskFull", "host3", severity="info")
    )

    response = client.get(
        "/api/alerts?severity=critical&severity=warning&sort=id&order=asc",
        headers=admin_headers,
    )

    assert response.status_code == 200

    payload = response.get_json()
    ids = {item["id"] for item in payload["items"]}

    assert critical_group.id in ids
    assert warning_group.id in ids
    assert info_group.id not in ids


def test_alerts_api_search_matches_child_alert_dedup_key(client, admin_headers, db):
    route = _route(group_by=["alertname", "severity"])

    group, _ = upsert_alert(_alert(route, "DiskFull", "host1"))
    upsert_alert(_alert(route, "DiskFull", "host2"))

    response = client.get(
        "/api/alerts?search=DiskFull:host2",
        headers=admin_headers,
    )

    assert response.status_code == 200

    payload = response.get_json()
    ids = {item["id"] for item in payload["items"]}

    assert group.id in ids


def test_alerts_api_search_matches_child_alert_labels(client, admin_headers, db):
    route = _route(group_by=["alertname", "severity"])

    group, _ = upsert_alert(_alert(route, "DiskFull", "host1"))
    upsert_alert(_alert(route, "DiskFull", "host2"))

    response = client.get(
        "/api/alerts?search=host2",
        headers=admin_headers,
    )

    assert response.status_code == 200

    payload = response.get_json()
    ids = {item["id"] for item in payload["items"]}

    assert group.id in ids
