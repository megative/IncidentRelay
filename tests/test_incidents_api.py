from uuid import uuid4

from app.api.schemas.roles import GROUP_USER_ADMIN_ROLE
from app.login import create_access_token
from app.modules.db import incidents_repo
from app.modules.db.models import AlertEvent, AlertGroup
from tests.factories import (
    add_user_to_team,
    create_group,
    create_route,
    create_team,
    create_user,
)


def unique_slug(prefix):
    return f"{prefix}-{uuid4().hex[:12]}"


def make_headers(user):
    token, _ = create_access_token(user)
    return {"Authorization": f"Bearer {token}"}


def create_incident_fixture():
    group = create_group(slug=unique_slug("group"))
    team = create_team(group=group, slug=unique_slug("team"), name="Platform Team")
    route = create_route(team=team)

    priority = incidents_repo.get_priority_by_slug("p3")

    incident = AlertGroup.create(
        team=team,
        route=route,
        service=route.service,
        rotation=route.rotation,
        escalation_policy=route.escalation_policy,
        source=route.source,
        group_key_hash=unique_slug("group-hash"),
        group_key=unique_slug("group-key"),
        title="DiskFull",
        message="/var is 95% full",
        severity="warning",
        status="firing",
        alert_count=0,
        firing_count=0,
        priority=priority.id if priority else None,
        priority_slug=priority.slug if priority else "p3",
        priority_order=priority.level if priority else 3,
        priority_set_manually=False,
        common_labels={
            "alertname": "DiskFull",
            "instance": "host1",
        },
        label_values={},
        payload_summary={},
    )

    return group, team, route, incident


def create_responder_headers(group, team):
    user = create_user(
        username=unique_slug("responder"),
        group=group,
        group_role=GROUP_USER_ADMIN_ROLE,
    )
    add_user_to_team(team, user, role="responder")
    return make_headers(user), user


def create_viewer_headers(group, team):
    user = create_user(
        username=unique_slug("viewer"),
        group=group,
        group_role="viewer",
    )
    add_user_to_team(team, user, role="viewer")
    return make_headers(user), user


def test_list_incident_priorities(client, db):
    group = create_group(slug=unique_slug("group"))
    user = create_user(
        username=unique_slug("user"),
        group=group,
        group_role="viewer",
    )

    response = client.get(
        "/api/incidents/priorities",
        headers=make_headers(user),
    )

    assert response.status_code == 200, response.get_json()

    payload = response.get_json()
    slugs = {item["slug"] for item in payload}

    assert {"p1", "p2", "p3", "p4", "p5"}.issubset(slugs)


def test_list_incidents_returns_incident_shape(client, db):
    group, team, route, incident = create_incident_fixture()
    headers, user = create_viewer_headers(group, team)

    response = client.get(
        f"/api/incidents?team_id={team.id}",
        headers=headers,
    )

    assert response.status_code == 200, response.get_json()

    payload = response.get_json()
    assert "items" in payload

    item = payload["items"][0]
    assert item["id"] == incident.id
    assert item["incident_id"] == incident.id
    assert item["priority"]["slug"] == "p3"
    assert item["maintenance"]["suppressed"] is False


def test_get_incident_includes_responders_and_stakeholders(client, db):
    group, team, route, incident = create_incident_fixture()
    headers, user = create_viewer_headers(group, team)

    response = client.get(
        f"/api/incidents/{incident.id}",
        headers=headers,
    )

    assert response.status_code == 200, response.get_json()

    payload = response.get_json()
    assert payload["incident_id"] == incident.id
    assert "responders" in payload
    assert "stakeholders" in payload
    assert "events" in payload
    assert "alerts" in payload


def test_update_incident_priority(client, db):
    group, team, route, incident = create_incident_fixture()
    headers, user = create_responder_headers(group, team)

    response = client.put(
        f"/api/incidents/{incident.id}/priority",
        json={"priority": "p1"},
        headers=headers,
    )

    assert response.status_code == 200, response.get_json()

    payload = response.get_json()
    assert payload["priority"]["slug"] == "p1"
    assert payload["priority"]["set_manually"] is True

    event = (
        AlertEvent
        .select()
        .where(
            AlertEvent.group == incident,
            AlertEvent.event_type == "priority_changed",
        )
        .get_or_none()
    )

    assert event is not None


def test_update_incident_priority_rejects_unknown_priority(client, db):
    group, team, route, incident = create_incident_fixture()
    headers, user = create_responder_headers(group, team)

    response = client.put(
        f"/api/incidents/{incident.id}/priority",
        json={"priority": "p99"},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_error"


def test_viewer_cannot_update_incident_priority(client, db):
    group, team, route, incident = create_incident_fixture()
    headers, user = create_viewer_headers(group, team)

    response = client.put(
        f"/api/incidents/{incident.id}/priority",
        json={"priority": "p1"},
        headers=headers,
    )

    assert response.status_code == 403


def test_add_user_responder_to_incident(client, db):
    group, team, route, incident = create_incident_fixture()
    headers, requester = create_responder_headers(group, team)

    target = create_user(
        username=unique_slug("target"),
        group=group,
        group_role="viewer",
    )
    add_user_to_team(team, target, role="responder")

    response = client.post(
        f"/api/incidents/{incident.id}/responders",
        json={
            "target_type": "user",
            "target_user_id": target.id,
            "message": "Please help with database checks",
            "expires_after_minutes": 30,
        },
        headers=headers,
    )

    assert response.status_code == 201, response.get_json()

    payload = response.get_json()
    assert payload["incident_id"] == incident.id
    assert payload["target_type"] == "user"
    assert payload["target_user_id"] == target.id
    assert payload["status"] == "requested"

    event = (
        AlertEvent
        .select()
        .where(
            AlertEvent.group == incident,
            AlertEvent.event_type == "responder_requested",
        )
        .get_or_none()
    )

    assert event is not None


def test_add_responder_requires_matching_target_id(client, db):
    group, team, route, incident = create_incident_fixture()
    headers, requester = create_responder_headers(group, team)

    response = client.post(
        f"/api/incidents/{incident.id}/responders",
        json={
            "target_type": "user",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_error"


def test_update_responder_status(client, db):
    group, team, route, incident = create_incident_fixture()
    headers, requester = create_responder_headers(group, team)

    target = create_user(
        username=unique_slug("target"),
        group=group,
        group_role="viewer",
    )
    add_user_to_team(team, target, role="responder")

    create_response = client.post(
        f"/api/incidents/{incident.id}/responders",
        json={
            "target_type": "user",
            "target_user_id": target.id,
        },
        headers=headers,
    )

    assert create_response.status_code == 201, create_response.get_json()

    responder_id = create_response.get_json()["id"]

    response = client.put(
        f"/api/incidents/{incident.id}/responders/{responder_id}",
        json={
            "status": "accepted",
            "response_message": "I am joining",
        },
        headers=headers,
    )

    assert response.status_code == 200, response.get_json()

    payload = response.get_json()
    assert payload["status"] == "accepted"
    assert payload["accepted_by_id"] == requester.id

    event = (
        AlertEvent
        .select()
        .where(
            AlertEvent.group == incident,
            AlertEvent.event_type == "responder_accepted",
        )
        .get_or_none()
    )

    assert event is not None


def test_add_email_stakeholder_to_incident(client, db):
    group, team, route, incident = create_incident_fixture()
    headers, user = create_responder_headers(group, team)

    response = client.post(
        f"/api/incidents/{incident.id}/stakeholders",
        json={
            "email": "manager@example.com",
            "display_name": "Manager",
            "role": "business_owner",
            "notify_on_created": True,
            "notify_on_priority_change": True,
            "notify_on_status_change": True,
            "notify_on_resolved": True,
        },
        headers=headers,
    )

    assert response.status_code == 201, response.get_json()

    payload = response.get_json()
    assert payload["incident_id"] == incident.id
    assert payload["email"] == "manager@example.com"
    assert payload["role"] == "business_owner"
    assert payload["active"] is True


def test_remove_incident_stakeholder(client, db):
    group, team, route, incident = create_incident_fixture()
    headers, user = create_responder_headers(group, team)

    create_response = client.post(
        f"/api/incidents/{incident.id}/stakeholders",
        json={
            "email": "manager@example.com",
            "display_name": "Manager",
            "role": "stakeholder",
        },
        headers=headers,
    )

    assert create_response.status_code == 201, create_response.get_json()

    stakeholder_id = create_response.get_json()["id"]

    response = client.delete(
        f"/api/incidents/{incident.id}/stakeholders/{stakeholder_id}",
        headers=headers,
    )

    assert response.status_code == 200, response.get_json()
    assert response.get_json()["deleted"] is True

    list_response = client.get(
        f"/api/incidents/{incident.id}/stakeholders",
        headers=headers,
    )

    assert list_response.status_code == 200
    assert list_response.get_json() == []
