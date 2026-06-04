from datetime import datetime, timedelta

from app.api.openapi.spec import build_openapi_spec
from app.api.schemas.rotations import RotationLayerMemberAddSchema
from app.modules.db import rotations_repo
from app.services.calendar_service import build_rotation_calendar
from tests.factories import (
    add_user_to_team,
    create_group,
    create_rotation,
    create_team,
    create_user,
)


def _team_with_users(*usernames):
    group = create_group()
    team = create_team(group)

    users = []
    for username in usernames:
        user = create_user(username=username, group=group)
        add_user_to_team(team, user)
        users.append(user)

    return team, users


def _parse_utc(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def _username_at(events, at):
    for event in events:
        start_at = _parse_utc(event["start"])
        end_at = _parse_utc(event["end"])

        if start_at <= at < end_at:
            return event["username"]

    return None


def _default_layer(rotation):
    return rotations_repo.get_or_create_default_layer(rotation.id)


def _layer_member_for_user(layer_id, user_id):
    members = rotations_repo.list_rotation_layer_members(
        layer_id,
        active_only=False,
        include_inactive_users=True,
    )

    for member in members:
        if member.user.id == user_id:
            return member

    raise AssertionError(f"user {user_id} was not found in layer {layer_id}")


def test_layer_member_delete_closes_period_instead_of_deleting():
    team, (alice,) = _team_with_users("alice")

    rotation = create_rotation(
        team,
        users=[alice],
        start_at=datetime(2026, 6, 1, 0, 0, 0),
        duration_seconds=86400,
    )

    layer = _default_layer(rotation)
    member = _layer_member_for_user(layer.id, alice.id)

    result = rotations_repo.delete_rotation_layer_member(member.id)

    closed = rotations_repo.get_rotation_layer_member(member.id)

    assert result["user_id"] == alice.id
    assert closed.active is False
    assert closed.ends_at is not None


def test_closed_layer_member_stays_visible_in_past_calendar_but_not_future():
    team, (alice, bob, charlie) = _team_with_users("alice", "bob", "charlie")

    rotation = create_rotation(
        team,
        users=[alice, bob, charlie],
        start_at=datetime(2026, 6, 1, 0, 0, 0),
        duration_seconds=86400,
    )

    layer = _default_layer(rotation)
    charlie_member = _layer_member_for_user(layer.id, charlie.id)

    charlie_member.active = False
    charlie_member.ends_at = datetime(2026, 6, 4, 0, 0, 0)
    charlie_member.save()

    events = build_rotation_calendar(
        rotation,
        datetime(2026, 6, 1, 0, 0, 0),
        datetime(2026, 6, 7, 0, 0, 0),
    )

    assert _username_at(events, datetime(2026, 6, 3, 12, 0, 0)) == "charlie"
    assert _username_at(events, datetime(2026, 6, 4, 12, 0, 0)) != "charlie"
    assert _username_at(events, datetime(2026, 6, 5, 12, 0, 0)) != "charlie"


def test_readding_removed_layer_member_creates_new_period_and_keeps_gap():
    team, (alice, bob, charlie) = _team_with_users("alice", "bob", "charlie")

    rotation = create_rotation(
        team,
        users=[alice, bob, charlie],
        start_at=datetime(2026, 6, 1, 0, 0, 0),
        duration_seconds=86400,
    )

    layer = _default_layer(rotation)
    old_charlie_member = _layer_member_for_user(layer.id, charlie.id)

    old_charlie_member.active = False
    old_charlie_member.ends_at = datetime(2026, 6, 4, 0, 0, 0)
    old_charlie_member.save()

    new_charlie_member = rotations_repo.add_rotation_layer_member(
        layer_id=layer.id,
        user_id=charlie.id,
        position=2,
        starts_at=datetime(2026, 6, 6, 0, 0, 0),
    )

    assert new_charlie_member.id != old_charlie_member.id
    assert new_charlie_member.starts_at == datetime(2026, 6, 6, 0, 0, 0)
    assert new_charlie_member.ends_at is None

    events = build_rotation_calendar(
        rotation,
        datetime(2026, 6, 1, 0, 0, 0),
        datetime(2026, 6, 9, 0, 0, 0),
    )

    assert _username_at(events, datetime(2026, 6, 3, 12, 0, 0)) == "charlie"
    assert _username_at(events, datetime(2026, 6, 4, 12, 0, 0)) != "charlie"
    assert _username_at(events, datetime(2026, 6, 5, 12, 0, 0)) != "charlie"
    assert _username_at(events, datetime(2026, 6, 6, 12, 0, 0)) == "charlie"


def test_future_layer_member_is_listed_but_not_effective_until_starts_at():
    team, (alice, bob, charlie) = _team_with_users("alice", "bob", "charlie")

    rotation = create_rotation(
        team,
        users=[alice, bob],
        start_at=datetime(2026, 6, 1, 0, 0, 0),
        duration_seconds=86400,
    )

    layer = _default_layer(rotation)

    future_member = rotations_repo.add_rotation_layer_member(
        layer_id=layer.id,
        user_id=charlie.id,
        position=2,
        starts_at=datetime(2026, 6, 5, 0, 0, 0),
    )

    open_members = rotations_repo.list_rotation_layer_members(
        layer.id,
        active_only=True,
        include_inactive_users=True,
    )

    effective_before_start = rotations_repo.list_rotation_layer_members(
        layer.id,
        active_only=True,
        at=datetime(2026, 6, 3, 0, 0, 0),
        include_inactive_users=True,
    )

    assert future_member.id in [member.id for member in open_members]
    assert future_member.id not in [member.id for member in effective_before_start]

    events = build_rotation_calendar(
        rotation,
        datetime(2026, 6, 1, 0, 0, 0),
        datetime(2026, 6, 8, 0, 0, 0),
    )

    names_before_start = [
        _username_at(events, datetime(2026, 6, day, 12, 0, 0))
        for day in (1, 2, 3, 4)
    ]

    assert "charlie" not in names_before_start
    assert _username_at(events, datetime(2026, 6, 6, 12, 0, 0)) == "charlie"


def test_rotation_layer_member_add_schema_accepts_optional_starts_at():
    payload = RotationLayerMemberAddSchema.model_validate(
        {
            "user_id": 1,
            "position": 0,
            "starts_at": "2026-06-10T09:00:00",
        }
    )

    assert payload.user_id == 1
    assert payload.position == 0
    assert payload.starts_at == datetime(2026, 6, 10, 9, 0, 0)


def test_openapi_documents_layer_member_starts_at():
    spec = build_openapi_spec()

    add_schema = (
        spec["paths"]["/api/rotations/layers/{layer_id}/members"]["post"]
        ["requestBody"]["content"]["application/json"]["schema"]
    )

    response_schema = (
        spec["paths"]["/api/rotations/layers/{layer_id}/members"]["get"]
        ["responses"]["200"]["content"]["application/json"]["schema"]
        ["items"]
    )

    assert add_schema["properties"]["starts_at"]["type"] == "string"
    assert add_schema["properties"]["starts_at"]["format"] == "date-time"
    assert add_schema["properties"]["starts_at"]["nullable"] is True

    assert response_schema["properties"]["starts_at"]["format"] == "date-time"
    assert response_schema["properties"]["ends_at"]["format"] == "date-time"
