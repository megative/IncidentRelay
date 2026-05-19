from datetime import datetime, timedelta

from app.modules.db import alerts_repo, channels_repo, groups_repo, locks_repo, routes_repo, teams_repo, tokens_repo
from app.modules.db.models import (
    AlertRouteChannel,
    ApiToken,
    AppLock,
    RotationMember,
    RotationOverride,
    TeamUser,
    UserGroup,
)
from tests.factories import (
    add_user_to_team,
    attach_channel,
    create_alert,
    create_channel,
    create_group,
    create_route,
    create_rotation,
    create_rotation_override,
    create_silence,
    create_team,
    create_user,
)


def test_alert_pagination_filters_searches_sorts_and_summarizes(db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    route = create_route(team)

    first = create_alert(route)
    first.title = "DiskFull"
    first.status = "firing"
    first.reminder_count = 2
    first.save()

    second = create_alert(route)
    second.title = "CPUHigh"
    second.status = "acknowledged"
    second.severity = "warning"
    second.save()

    result = alerts_repo.paginate_alerts(
        team_ids=[team.id],
        page=1,
        page_size=1,
        sort="id",
        order="asc",
    )

    assert result["pagination"]["total_items"] == 2
    assert result["pagination"]["total_pages"] == 2
    assert result["summary"]["firing"] == 1
    assert result["summary"]["acknowledged"] == 1
    assert result["summary"]["reminders"] == 2
    assert result["items"][0].id == first.id

    search_result = alerts_repo.paginate_alerts(team_ids=[team.id], search="CPU")
    assert [item.title for item in search_result["items"]] == ["CPUHigh"]

    empty = alerts_repo.paginate_alerts(team_ids=[])
    assert empty["items"] == []
    assert empty["pagination"]["total_items"] == 0


def test_route_channel_link_helpers_replace_and_unlink_links(db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    route = create_route(team)
    first = create_channel(group, team)
    second = create_channel(group, team)

    routes_repo.replace_route_channels(route.id, [first.id, second.id])
    assert AlertRouteChannel.select().where(AlertRouteChannel.route == route.id).count() == 2

    routes_repo.replace_route_channels(route.id, [second.id])
    assert AlertRouteChannel.select().where(AlertRouteChannel.route == route.id).count() == 1

    assert routes_repo.unlink_route_channel(route.id, second.id) == 1
    assert AlertRouteChannel.select().where(AlertRouteChannel.route == route.id).count() == 0


def test_delete_channel_soft_deletes_channel_and_removes_route_links(db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    route = create_route(team)
    channel = create_channel(group, team)
    attach_channel(route, channel)

    deleted = channels_repo.delete_channel(channel.id)

    assert deleted.deleted is True
    assert deleted.enabled is False
    assert deleted.deleted_at is not None
    assert AlertRouteChannel.select().where(AlertRouteChannel.channel == channel.id).count() == 0


def test_soft_delete_route_disables_route_and_removes_channel_links(db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    route = create_route(team)
    channel = create_channel(group, team)
    attach_channel(route, channel)

    deleted = routes_repo.soft_delete_route(route.id)

    assert deleted.deleted is True
    assert deleted.enabled is False
    assert deleted.deleted_at is not None
    assert AlertRouteChannel.select().where(AlertRouteChannel.route == route.id).count() == 0


def test_soft_delete_group_disables_child_resources_and_tokens(db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    user = create_user("alice", group)
    rotation = create_rotation(team)
    route = create_route(team, rotation=rotation)
    channel = create_channel(group, team)
    silence = create_silence(team)
    token = ApiToken.create(
        user=user,
        group=group,
        team=team,
        name="token",
        token_prefix="prefix",
        token_hash="hash",
        scopes=["*"],
    )

    deleted = groups_repo.soft_delete_group(group.id)

    assert deleted.deleted is True
    assert deleted.active is False

    assert type(team).get_by_id(team.id).deleted is True
    assert type(team).get_by_id(team.id).active is False
    assert type(rotation).get_by_id(rotation.id).deleted is True
    assert type(rotation).get_by_id(rotation.id).enabled is False
    assert type(route).get_by_id(route.id).deleted is True
    assert type(route).get_by_id(route.id).enabled is False
    assert type(channel).get_by_id(channel.id).deleted is True
    assert type(channel).get_by_id(channel.id).enabled is False
    assert type(silence).get_by_id(silence.id).deleted is True
    assert type(silence).get_by_id(silence.id).enabled is False
    assert ApiToken.get_by_id(token.id).deleted is True
    assert ApiToken.get_by_id(token.id).active is False


def test_delete_group_membership_removes_user_from_group_teams_and_rotations(db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    user = create_user("alice", group)
    membership = UserGroup.get(UserGroup.user == user.id, UserGroup.group == group.id)
    add_user_to_team(team, user)
    rotation = create_rotation(team, users=[user])
    create_rotation_override(rotation, user)

    result = groups_repo.delete_group_membership(membership.id)

    assert result["group_id"] == group.id
    assert result["user_id"] == user.id
    assert UserGroup.select().where(UserGroup.id == membership.id).count() == 0
    assert TeamUser.select().where((TeamUser.user == user.id) & (TeamUser.team == team.id)).count() == 0
    assert RotationMember.select().where(RotationMember.user == user.id).count() == 0
    assert RotationOverride.select().where(RotationOverride.user == user.id).count() == 0


def test_delete_team_membership_removes_user_from_team_rotations_only(db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    user = create_user("alice", group)
    team_membership = add_user_to_team(team, user)
    rotation = create_rotation(team, users=[user])
    create_rotation_override(rotation, user)

    result = teams_repo.delete_team_membership(team_membership.id)

    assert result["team_id"] == team.id
    assert result["group_id"] == group.id
    assert result["user_id"] == user.id
    assert TeamUser.select().where(TeamUser.id == team_membership.id).count() == 0
    assert RotationMember.select().where(RotationMember.user == user.id).count() == 0
    assert RotationOverride.select().where(RotationOverride.user == user.id).count() == 0
    assert UserGroup.select().where(UserGroup.user == user.id, UserGroup.group == group.id).exists()


def test_token_repo_revokes_and_hides_user_tokens(db):
    group = create_group(slug="infra")
    user = create_user("alice", group)
    token = tokens_repo.create_api_token(
        name="cli",
        token_prefix="prefix",
        token_hash="hash",
        scopes=["alerts:write"],
        user_id=user.id,
        group_id=group.id,
    )

    assert tokens_repo.list_user_tokens(user.id) == [token]
    assert tokens_repo.get_active_token_by_hash("hash") == token

    revoked = tokens_repo.revoke_user_token(token.id, user.id)

    assert revoked.active is False
    assert revoked.deleted is True
    assert tokens_repo.list_user_tokens(user.id) == []
    assert tokens_repo.get_active_token_by_hash("hash") is None


def test_locks_repo_acquires_rejects_busy_steals_expired_and_releases(db):
    assert locks_repo.acquire_lock("job", "owner-1", ttl_seconds=60) is True
    assert locks_repo.acquire_lock("job", "owner-2", ttl_seconds=60) is False

    lock = AppLock.get(AppLock.name == "job")
    lock.expires_at = datetime.utcnow() - timedelta(seconds=1)
    lock.save()

    assert locks_repo.acquire_lock("job", "owner-2", ttl_seconds=60) is True
    assert locks_repo.release_lock("job", "owner-1") == 0
    assert locks_repo.release_lock("job", "owner-2") == 1
