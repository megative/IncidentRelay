import pytest
from peewee import IntegrityError

from app.modules.db.models import Group, NotificationChannel, Team, UserGroup
from tests.factories import create_channel, create_group, create_team, create_user


def test_group_slug_is_unique(db):
    create_group(name="Infra", slug="infra")

    with pytest.raises(IntegrityError):
        create_group(name="Infra duplicate", slug="infra")


def test_user_can_belong_to_group(db):
    group = create_group(slug="infra")
    user = create_user(username="ivan", group=group)

    assert UserGroup.select().where(UserGroup.user == user, UserGroup.group == group).exists()
    assert user.active_group == group


def test_team_belongs_to_group(db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")

    fetched = Team.get_by_id(team.id)

    assert fetched.group == group
    assert fetched.slug == "sre"


def test_json_field_round_trip_for_channel_config(db):
    group = create_group(slug="infra")
    channel = create_channel(
        group,
        config={
            "url": "https://example.com/webhook",
            "headers": {"X-Test": "yes"},
            "enabled": True,
            "retries": [1, 2, 3],
        },
    )

    fetched = NotificationChannel.get_by_id(channel.id)

    assert fetched.config["headers"]["X-Test"] == "yes"
    assert fetched.config["enabled"] is True
    assert fetched.config["retries"] == [1, 2, 3]


def test_soft_active_flags_default_to_enabled(db):
    group = Group.create(name="Infra", slug="infra")
    user = create_user(username="alice", group=group)
    team = create_team(group, slug="sre")

    assert group.is_active is True
    assert user.is_active is True
    assert team.is_active is True
