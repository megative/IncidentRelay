from tests.factories import create_group, create_team, create_user


def test_add_team_user_respects_active_checkbox(client, admin_headers):
    group = create_group()
    team = create_team(group=group)
    user = create_user(group=group)

    response = client.post(
        f"/api/teams/{team.id}/users",
        json={
            "user_id": user.id,
            "role": "viewer",
            "active": False,
        },
        headers=admin_headers,
    )

    assert response.status_code == 201

    data = response.get_json()
    assert data["active"] is False

    members_response = client.get(
        f"/api/teams/{team.id}/users",
        headers=admin_headers,
    )

    assert members_response.status_code == 200

    members = members_response.get_json()
    membership = next(item for item in members if item["user_id"] == user.id)

    assert membership["active"] is False
