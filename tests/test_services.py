import pytest
from pydantic import ValidationError

from app.api.schemas.services import (
    ServiceCreateSchema,
    ServiceDependencyCreateSchema,
    ServiceMatchRuleCreateSchema,
)
from app.modules.db.models import (
    Alert,
    ServiceDependency,
    ServiceLink,
    ServiceMatchRule,
    ServiceRunbook,
)
from tests.factories import (
    create_group,
    create_route,
    create_service,
    create_team,
)


def create_service_alert(
    *,
    team,
    route,
    service,
    fingerprint,
    status="firing",
    severity="critical",
    alertname="TestAlert",
    summary="Test alert",
):
    labels = {
        "alertname": alertname,
        "severity": severity,
    }
    annotations = {
        "summary": summary,
    }

    return Alert.create(
        route=route,
        team=team,
        service=service,
        source=getattr(route, "source", None) or "alertmanager",
        external_id=fingerprint,
        dedup_key=fingerprint,
        group_key=fingerprint,
        title=summary,
        message=summary,
        severity=severity,
        labels=labels,
        payload={
            "status": status,
            "labels": labels,
            "annotations": annotations,
            "fingerprint": fingerprint,
        },
        status=status,
    )


def service_payload(team, **overrides):
    payload = {
        "team_id": team.id,
        "slug": "rabbitmq-cloud",
        "name": "RabbitMQ Cloud",
        "description": "Shared RabbitMQ cluster",
        "service_type": "queue",
        "environment": "production",
        "criticality": "critical",
        "tier": "tier_1",
        "status": "operational",
        "status_source": "manual",
        "labels": {"system": "messaging"},
        "tags": ["rabbitmq", "production"],
        "metadata": {},
        "enabled": True,
        "public": False,
        "public_order": 100,
    }
    payload.update(overrides)
    return payload


def test_service_schema_accepts_valid_payload():
    group = create_group()
    team = create_team(group)

    schema = ServiceCreateSchema(**service_payload(team))

    assert schema.team_id == team.id
    assert schema.slug == "rabbitmq-cloud"
    assert schema.service_type == "queue"
    assert schema.environment == "production"
    assert schema.criticality == "critical"
    assert schema.tier == "tier_1"
    assert schema.status == "operational"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("slug", "RabbitMQ Cloud"),
        ("service_type", "unknown-type"),
        ("environment", "prod"),
        ("criticality", "blocker"),
        ("tier", "tier_0"),
        ("status", "broken"),
        ("status_source", "operator"),
    ],
)
def test_service_schema_rejects_invalid_enums_and_slug(field, value):
    group = create_group()
    team = create_team(group)
    payload = service_payload(team, **{field: value})

    with pytest.raises(ValidationError):
        ServiceCreateSchema(**payload)


def test_service_match_rule_schema_requires_matchers():
    group = create_group()
    team = create_team(group)
    service = create_service(team)

    with pytest.raises(ValidationError):
        ServiceMatchRuleCreateSchema(
            team_id=team.id,
            service_id=service.id,
            name="Empty match rule",
            matchers={},
        )


def test_service_match_rule_schema_accepts_label_regex_matcher():
    group = create_group()
    team = create_team(group)
    service = create_service(team)
    route = create_route(team)

    schema = ServiceMatchRuleCreateSchema(
        team_id=team.id,
        route_id=route.id,
        service_id=service.id,
        name="RabbitMQ Cloud labels",
        position=10,
        enabled=True,
        matchers={
            "labels": {
                "job": "RabbitMQ",
                "rabbitmq": {
                    "op": "regex",
                    "value": "^rabbitmq-cloud$",
                },
            }
        },
    )

    assert schema.team_id == team.id
    assert schema.route_id == route.id
    assert schema.service_id == service.id
    assert schema.matchers["labels"]["job"] == "RabbitMQ"


def test_service_dependency_schema_rejects_self_dependency():
    group = create_group()
    team = create_team(group)
    service = create_service(team)

    with pytest.raises(ValidationError):
        ServiceDependencyCreateSchema(
            service_id=service.id,
            depends_on_service_id=service.id,
            dependency_type="hard",
            criticality="required",
        )


def test_create_and_list_services_api(client, admin_headers):
    group = create_group()
    team = create_team(group)

    response = client.post(
        "/api/services",
        json=service_payload(team),
        headers=admin_headers,
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["id"]
    assert data["team_id"] == team.id
    assert data["slug"] == "rabbitmq-cloud"
    assert data["name"] == "RabbitMQ Cloud"
    assert data["service_type"] == "queue"
    assert data["criticality"] == "critical"

    response = client.get(
        f"/api/services?team_id={team.id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    items = response.get_json()
    assert any(item["slug"] == "rabbitmq-cloud" for item in items)


def test_get_update_and_delete_service_api(client, admin_headers):
    group = create_group()
    team = create_team(group)
    service = create_service(team, slug="billing-api", name="Billing API")

    response = client.get(
        f"/api/services/{service.id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["slug"] == "billing-api"

    response = client.put(
        f"/api/services/{service.id}",
        json=service_payload(
            team,
            slug="billing-api",
            name="Billing API",
            status="degraded",
            status_message="High latency",
            criticality="high",
        ),
        headers=admin_headers,
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "degraded"
    assert data["status_message"] == "High latency"
    assert data["criticality"] == "high"

    response = client.delete(
        f"/api/services/{service.id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["deleted"] is True

    response = client.get(
        f"/api/services/{service.id}",
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_service_slug_must_be_unique_inside_team(client, admin_headers):
    group = create_group()
    team = create_team(group)

    first = client.post(
        "/api/services",
        json=service_payload(team, slug="rabbitmq-cloud"),
        headers=admin_headers,
    )
    assert first.status_code == 201

    duplicate = client.post(
        "/api/services",
        json=service_payload(team, slug="rabbitmq-cloud"),
        headers=admin_headers,
    )
    assert duplicate.status_code == 409


def test_create_and_list_service_match_rules_api(client, admin_headers):
    group = create_group()
    team = create_team(group)
    service = create_service(team)
    route = create_route(team)

    response = client.post(
        f"/api/services/{service.id}/match-rules",
        json={
            "team_id": team.id,
            "route_id": route.id,
            "service_id": service.id,
            "name": "RabbitMQ Cloud labels",
            "position": 10,
            "enabled": True,
            "matchers": {
                "labels": {
                    "job": "RabbitMQ",
                    "rabbitmq": {
                        "op": "regex",
                        "value": "^rabbitmq-cloud$",
                    },
                }
            },
        },
        headers=admin_headers,
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["id"]
    assert data["team_id"] == team.id
    assert data["service_id"] == service.id
    assert data["route_id"] == route.id
    assert data["matchers"]["labels"]["job"] == "RabbitMQ"

    response = client.get(
        f"/api/services/match-rules?service_id={service.id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    items = response.get_json()
    assert len(items) == 1
    assert items[0]["name"] == "RabbitMQ Cloud labels"


def test_update_and_delete_service_match_rule_api(client, admin_headers):
    group = create_group()
    team = create_team(group)
    service = create_service(team)

    rule = ServiceMatchRule.create(
        team=team,
        service=service,
        name="Old rule",
        position=10,
        enabled=True,
        matchers={"labels": {"job": "old"}},
    )

    response = client.put(
        f"/api/services/match-rules/{rule.id}",
        json={
            "team_id": team.id,
            "service_id": service.id,
            "name": "New rule",
            "position": 20,
            "enabled": False,
            "matchers": {"labels": {"job": "new"}},
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["name"] == "New rule"
    assert data["position"] == 20
    assert data["enabled"] is False

    response = client.delete(
        f"/api/services/match-rules/{rule.id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["deleted"] is True


def test_create_list_update_delete_service_links_api(client, admin_headers):
    group = create_group()
    team = create_team(group)
    service = create_service(team)

    response = client.post(
        f"/api/services/{service.id}/links",
        json={
            "link_type": "dashboard",
            "label": "Grafana",
            "url": "https://grafana.example.com/d/rabbitmq-cloud",
            "priority": 10,
            "enabled": True,
        },
        headers=admin_headers,
    )

    assert response.status_code == 201
    link = response.get_json()
    assert link["label"] == "Grafana"
    assert link["link_type"] == "dashboard"
    assert link["service_id"] == service.id
    assert link["service_name"] == service.name
    assert link["service_slug"] == service.slug
    assert link["team_id"] == team.id
    assert link["team_name"] == team.name
    assert link["team_slug"] == team.slug

    response = client.get(
        f"/api/services/{service.id}/links",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert len(response.get_json()) == 1

    response = client.put(
        f"/api/services/links/{link['id']}",
        json={
            "link_type": "logs",
            "label": "Loki",
            "url": "https://logs.example.com",
            "priority": 20,
            "enabled": False,
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["link_type"] == "logs"

    response = client.delete(
        f"/api/services/links/{link['id']}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["deleted"] is True


def test_create_list_update_delete_service_runbooks_api(client, admin_headers):
    group = create_group()
    team = create_team(group)
    service = create_service(team)

    response = client.post(
        f"/api/services/{service.id}/runbooks",
        json={
            "title": "RabbitMQ cluster partition",
            "url": "https://docs.example.com/runbooks/rabbitmq/cluster-partition",
            "severity": "critical",
            "priority": 10,
            "enabled": True,
            "matchers": {
                "labels": {
                    "alertname": "RabbitMQClusterPartition",
                }
            },
        },
        headers=admin_headers,
    )

    assert response.status_code == 201
    runbook = response.get_json()
    assert runbook["title"] == "RabbitMQ cluster partition"
    assert runbook["severity"] == "critical"

    response = client.get(
        f"/api/services/{service.id}/runbooks",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert len(response.get_json()) == 1

    response = client.put(
        f"/api/services/runbooks/{runbook['id']}",
        json={
            "title": "Updated runbook",
            "url": "https://docs.example.com/runbooks/rabbitmq/updated",
            "severity": "warning",
            "priority": 20,
            "enabled": False,
            "matchers": {},
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["title"] == "Updated runbook"

    response = client.delete(
        f"/api/services/runbooks/{runbook['id']}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["deleted"] is True


def test_create_list_update_delete_service_dependencies_api(client, admin_headers):
    group = create_group()
    team = create_team(group)
    service = create_service(team, slug="billing-api", name="Billing API")
    upstream = create_service(team, slug="postgresql-prod", name="PostgreSQL Prod")

    response = client.post(
        f"/api/services/{service.id}/dependencies",
        json={
            "depends_on_service_id": upstream.id,
            "dependency_type": "hard",
            "criticality": "required",
            "description": "Billing API stores data in PostgreSQL",
            "enabled": True,
        },
        headers=admin_headers,
    )

    assert response.status_code == 201
    dependency = response.get_json()
    assert dependency["depends_on_service_id"] == upstream.id
    assert dependency["dependency_type"] == "hard"
    assert dependency["criticality"] == "required"

    response = client.get(
        f"/api/services/{service.id}/dependencies",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert len(response.get_json()) == 1

    response = client.put(
        f"/api/services/dependencies/{dependency['id']}",
        json={
            "depends_on_service_id": upstream.id,
            "dependency_type": "soft",
            "criticality": "important",
            "enabled": False,
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["dependency_type"] == "soft"

    response = client.delete(
        f"/api/services/dependencies/{dependency['id']}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["deleted"] is True


def test_service_aggregate_links_runbooks_and_dependencies_api(client, admin_headers):
    group = create_group()
    team = create_team(group)
    service = create_service(team, slug="rabbitmq-cloud", name="RabbitMQ Cloud")
    upstream = create_service(team, slug="network-prod", name="Network Prod")

    ServiceLink.create(
        service=service,
        link_type="dashboard",
        label="Grafana",
        url="https://grafana.example.com",
        priority=10,
        enabled=True,
    )
    ServiceRunbook.create(
        service=service,
        title="RabbitMQ runbook",
        url="https://docs.example.com/runbooks/rabbitmq",
        priority=10,
        enabled=True,
        matchers={},
    )
    ServiceDependency.create(
        service=service,
        depends_on_service=upstream,
        dependency_type="hard",
        criticality="required",
        enabled=True,
    )

    response = client.get(
        f"/api/services/links?service_id={service.id}",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert len(response.get_json()) == 1

    response = client.get(
        f"/api/services/runbooks?service_id={service.id}",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert len(response.get_json()) == 1

    response = client.get(
        f"/api/services/dependencies?service_id={service.id}",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert len(response.get_json()) == 1


def test_service_analytics_counts_alerts_by_service(client, admin_headers):
    group = create_group()
    team = create_team(group)
    service = create_service(team, slug="rabbitmq-cloud", name="RabbitMQ Cloud")
    route = create_route(team, service=service)

    create_service_alert(
        team=team,
        route=route,
        service=service,
        fingerprint="rabbitmq-cloud-critical-1",
        status="firing",
        severity="critical",
        alertname="RabbitMQClusterPartition",
        summary="RabbitMQ cluster partition",
    )

    response = client.get(
        f"/api/services/analytics?service_id={service.id}&days=30",
        headers=admin_headers,
    )

    assert response.status_code == 200
    rows = response.get_json()
    assert len(rows) == 1
    assert rows[0]["service_id"] == service.id
    assert rows[0]["total_alerts"] == 1
    assert rows[0]["open_alerts"] == 1
    assert rows[0]["critical_open_alerts"] == 1


def test_service_impact_reports_alert_impact(client, admin_headers):
    group = create_group()
    team = create_team(group)
    service = create_service(team, slug="rabbitmq-cloud", name="RabbitMQ Cloud")
    route = create_route(team, service=service)

    create_service_alert(
        team=team,
        route=route,
        service=service,
        fingerprint="rabbitmq-cloud-critical-impact",
        status="firing",
        severity="critical",
        alertname="RabbitMQClusterPartition",
        summary="RabbitMQ cluster partition",
    )

    response = client.get(
        f"/api/services/impact?service_id={service.id}&days=30",
        headers=admin_headers,
    )

    assert response.status_code == 200
    rows = response.get_json()
    assert len(rows) == 1
    assert rows[0]["service_id"] == service.id
    assert rows[0]["has_alert_impact"] is True
    assert rows[0]["critical_open_alerts"] == 1
    assert rows[0]["effective_status"] in {
        "degraded",
        "partial_outage",
        "major_outage",
    }


def test_service_impact_reports_dependency_impact(client, admin_headers):
    group = create_group()
    team = create_team(group)

    frontend = create_service(team, slug="frontend-web", name="Frontend Web")
    api = create_service(team, slug="billing-api", name="Billing API")
    route = create_route(team, service=api)

    ServiceDependency.create(
        service=frontend,
        depends_on_service=api,
        dependency_type="hard",
        criticality="required",
        enabled=True,
    )

    create_service_alert(
        team=team,
        route=route,
        service=api,
        fingerprint="billing-api-critical-impact",
        status="firing",
        severity="critical",
        alertname="BillingApiDown",
        summary="Billing API is down",
    )

    response = client.get(
        f"/api/services/impact?service_id={frontend.id}&days=30",
        headers=admin_headers,
    )

    assert response.status_code == 200
    rows = response.get_json()
    assert len(rows) == 1
    assert rows[0]["service_id"] == frontend.id
    assert rows[0]["has_dependency_impact"] is True
    assert rows[0]["upstream_issues_count"] >= 1
