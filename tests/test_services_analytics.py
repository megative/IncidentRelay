from app.login import create_access_token
from app.modules.db import services_repo
from tests.factories import (
    add_user_to_team,
    create_group,
    create_team,
    create_user,
    unique,
)


def make_headers(user):
    token, _ = create_access_token(user)
    return {"Authorization": f"Bearer {token}"}


def create_test_service(team, *, name, enabled=True):
    return services_repo.create_service({
        "team": team.id,
        "slug": unique("service"),
        "name": name,
        "description": "",
        "service_type": "application",
        "environment": "prod",
        "criticality": "medium",
        "tier": "backend",
        "status": "operational",
        "status_source": "manual",
        "status_message": "",
        "default_rotation": None,
        "default_escalation_policy": None,
        "labels": {},
        "tags": [],
        "metadata": {},
        "enabled": enabled,
        "public": False,
        "public_name": "",
        "public_description": "",
        "public_order": 0,
    })


def test_service_analytics_does_not_include_disabled_service(client, db):
    group = create_group(slug=unique("group"))
    team = create_team(group=group, slug=unique("team"))

    user = create_user(
        username=unique("viewer"),
        group=group,
        group_role="viewer",
    )
    add_user_to_team(team, user, role="viewer")

    active_service = create_test_service(
        team,
        name="Active service",
        enabled=True,
    )
    disabled_service = create_test_service(
        team,
        name="Disabled service",
        enabled=False,
    )

    response = client.get(
        f"/api/services/analytics?team_id={team.id}",
        headers=make_headers(user),
    )

    assert response.status_code == 200, response.get_json()

    payload = response.get_json()
    service_ids = {item["service_id"] for item in payload}

    assert active_service.id in service_ids
    assert disabled_service.id not in service_ids


def test_service_analytics_does_not_include_deleted_service(client, db):
    group = create_group(slug=unique("group"))
    team = create_team(group=group, slug=unique("team"))

    user = create_user(
        username=unique("viewer"),
        group=group,
        group_role="viewer",
    )
    add_user_to_team(team, user, role="viewer")

    deleted_service = create_test_service(
        team,
        name="Deleted service",
        enabled=True,
    )
    services_repo.soft_delete_service(deleted_service.id)

    response = client.get(
        f"/api/services/analytics?team_id={team.id}",
        headers=make_headers(user),
    )

    assert response.status_code == 200, response.get_json()

    payload = response.get_json()

    assert all(
        item["service_id"] != deleted_service.id
        for item in payload
    )


def test_service_analytics_returns_404_for_disabled_service_filter(client, db):
    group = create_group(slug=unique("group"))
    team = create_team(group=group, slug=unique("team"))

    user = create_user(
        username=unique("viewer"),
        group=group,
        group_role="viewer",
    )
    add_user_to_team(team, user, role="viewer")

    disabled_service = create_test_service(
        team,
        name="Disabled service",
        enabled=False,
    )

    response = client.get(
        f"/api/services/analytics?service_id={disabled_service.id}",
        headers=make_headers(user),
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "service_not_found"
