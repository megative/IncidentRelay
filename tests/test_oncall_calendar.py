from datetime import datetime, timedelta

from app.services.calendar_service import build_rotation_calendar, parse_date_or_datetime
from app.services.oncall import get_current_oncall_user, get_next_rotation_user
from tests.factories import (
    add_user_to_team,
    create_group,
    create_rotation,
    create_rotation_override,
    create_team,
    create_user,
)


def test_get_current_oncall_user_rotates_by_duration(db):
    start = datetime(2026, 5, 18, 9, 0, 0)
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    alice = create_user("alice", group)
    bob = create_user("bob", group)
    add_user_to_team(team, alice)
    add_user_to_team(team, bob)
    rotation = create_rotation(
        team,
        users=[alice, bob],
        start_at=start,
        duration_seconds=3600,
    )

    assert get_current_oncall_user(rotation, start).username == "alice"
    assert get_current_oncall_user(rotation, start + timedelta(hours=1)).username == "bob"
    assert get_current_oncall_user(rotation, start + timedelta(hours=2)).username == "alice"


def test_get_current_oncall_user_prefers_active_override(db):
    start = datetime(2026, 5, 18, 9, 0, 0)
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    alice = create_user("alice", group)
    bob = create_user("bob", group)
    rotation = create_rotation(
        team,
        users=[alice],
        start_at=start,
        duration_seconds=3600,
    )
    create_rotation_override(
        rotation,
        bob,
        starts_at=start - timedelta(minutes=10),
        ends_at=start + timedelta(minutes=10),
    )

    assert get_current_oncall_user(rotation, start).username == "bob"


def test_get_next_rotation_user_returns_next_member(db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    alice = create_user("alice", group)
    bob = create_user("bob", group)
    rotation = create_rotation(team, users=[alice, bob])

    assert get_next_rotation_user(rotation, alice).username == "bob"
    assert get_next_rotation_user(rotation, bob).username == "alice"


def test_parse_date_or_datetime_accepts_date_and_datetime():
    assert parse_date_or_datetime("2026-05-18") == datetime(2026, 5, 18, 0, 0, 0)
    assert parse_date_or_datetime("2026-05-18T09:30:00") == datetime(2026, 5, 18, 9, 30, 0)


def test_build_rotation_calendar_returns_slots(db):
    start = datetime(2026, 5, 18, 9, 0, 0)
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    alice = create_user("alice", group)
    bob = create_user("bob", group)
    rotation = create_rotation(
        team,
        users=[alice, bob],
        start_at=start,
        duration_seconds=3600,
    )

    events = build_rotation_calendar(
        rotation,
        start,
        start + timedelta(hours=2),
    )

    assert [event["username"] for event in events] == ["alice", "bob"]
    assert events[0]["type"] == "layer"
    assert events[0]["layer_name"] == "Default layer"
    assert events[0]["team_slug"] == "sre"
