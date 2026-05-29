from app.modules.db.models import Alert, ServiceLink, ServiceRunbook
from app.services.notification_service import format_alert_message
from app.services.service_context import (
    format_service_context_plain,
    get_alert_service_runbooks,
)
from tests.factories import create_group, create_route, create_service, create_team


def create_alert_for_service(team, route, service, *, alertname="RabbitMQClusterPartition"):
    return Alert.create(
        route=route,
        team=team,
        service=service,
        source=getattr(route, "source", None) or "alertmanager",
        external_id="service-context-test",
        dedup_key="service-context-test",
        group_key="service-context-test",
        title="RabbitMQ Cluster Partition",
        message="RabbitMQ cluster partition detected",
        severity="critical",
        status="firing",
        labels={
            "alertname": alertname,
            "severity": "critical",
        },
        payload={
            "labels": {
                "alertname": alertname,
                "severity": "critical",
            },
            "annotations": {
                "summary": "RabbitMQ cluster partition detected",
            },
        },
    )


def test_format_alert_message_includes_service_links_and_runbooks():
    group = create_group()
    team = create_team(group, name="Infra", slug="infra")
    service = create_service(team, name="RabbitMQ Cloud", slug="rabbitmq-cloud")
    route = create_route(team, service=service)

    ServiceLink.create(
        service=service,
        link_type="dashboard",
        label="Grafana",
        url="https://grafana.example.com/d/rabbitmq-cloud",
        priority=10,
        enabled=True,
    )
    ServiceRunbook.create(
        service=service,
        title="RabbitMQ cluster partition",
        url="https://docs.example.com/runbooks/rabbitmq/cluster-partition",
        severity="critical",
        matchers={
            "labels": {
                "alertname": "RabbitMQClusterPartition",
            }
        },
        priority=10,
        enabled=True,
    )

    alert = create_alert_for_service(team, route, service)
    text = format_alert_message(alert)

    assert "Service: RabbitMQ Cloud" in text
    assert "Links:" in text
    assert "Grafana: https://grafana.example.com/d/rabbitmq-cloud" in text
    assert "Runbooks:" in text
    assert (
        "RabbitMQ cluster partition (critical): "
        "https://docs.example.com/runbooks/rabbitmq/cluster-partition"
    ) in text


def test_runbook_with_empty_matchers_is_generic_for_service():
    group = create_group()
    team = create_team(group)
    service = create_service(team, name="RabbitMQ Cloud", slug="rabbitmq-cloud")
    route = create_route(team, service=service)

    ServiceRunbook.create(
        service=service,
        title="Generic RabbitMQ troubleshooting",
        url="https://docs.example.com/runbooks/rabbitmq",
        matchers={},
        priority=100,
        enabled=True,
    )

    alert = create_alert_for_service(team, route, service)
    runbooks = get_alert_service_runbooks(alert)

    assert len(runbooks) == 1
    assert runbooks[0].title == "Generic RabbitMQ troubleshooting"


def test_runbook_matchers_filter_by_alert_labels():
    group = create_group()
    team = create_team(group)
    service = create_service(team, name="RabbitMQ Cloud", slug="rabbitmq-cloud")
    route = create_route(team, service=service)

    ServiceRunbook.create(
        service=service,
        title="RabbitMQ cluster partition",
        url="https://docs.example.com/runbooks/rabbitmq/cluster-partition",
        matchers={
            "labels": {
                "alertname": "RabbitMQClusterPartition",
            }
        },
        priority=10,
        enabled=True,
    )
    ServiceRunbook.create(
        service=service,
        title="RabbitMQ disk low",
        url="https://docs.example.com/runbooks/rabbitmq/disk-low",
        matchers={
            "labels": {
                "alertname": "RabbitMQDiskLow",
            }
        },
        priority=20,
        enabled=True,
    )

    alert = create_alert_for_service(
        team,
        route,
        service,
        alertname="RabbitMQClusterPartition",
    )

    runbooks = get_alert_service_runbooks(alert)

    assert [item.title for item in runbooks] == ["RabbitMQ cluster partition"]


def test_disabled_links_and_runbooks_are_not_included():
    group = create_group()
    team = create_team(group)
    service = create_service(team)
    route = create_route(team, service=service)

    ServiceLink.create(
        service=service,
        link_type="dashboard",
        label="Disabled Grafana",
        url="https://grafana.example.com",
        priority=10,
        enabled=False,
    )
    ServiceRunbook.create(
        service=service,
        title="Disabled runbook",
        url="https://docs.example.com/runbooks/disabled",
        matchers={},
        priority=10,
        enabled=False,
    )

    alert = create_alert_for_service(team, route, service)
    lines = format_service_context_plain(alert)

    assert lines == []
