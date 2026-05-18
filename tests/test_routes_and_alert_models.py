from app.modules.db.models import Alert, AlertRouteChannel, RotationMember
from tests.factories import (
    add_user_to_team,
    attach_channel,
    create_alert,
    create_channel,
    create_group,
    create_route,
    create_rotation,
    create_team,
    create_user,
)


def test_rotation_members_are_ordered_by_position(db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    first = create_user("alice", group)
    second = create_user("bob", group)

    add_user_to_team(team, first)
    add_user_to_team(team, second)
    rotation = create_rotation(team, users=[first, second])

    members = list(
        RotationMember.select()
        .where(RotationMember.rotation == rotation)
        .order_by(RotationMember.position.asc())
    )

    assert [member.user.username for member in members] == ["alice", "bob"]


def test_route_can_have_notification_channel(db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    channel = create_channel(group)
    route = create_route(group, team)

    attach_channel(route, channel)

    assert AlertRouteChannel.select().where(AlertRouteChannel.route == route).count() == 1


def test_alert_is_persisted_with_labels_and_annotations(db):
    group = create_group(slug="infra")
    team = create_team(group, slug="sre")
    route = create_route(group, team)

    alert = create_alert(route)

    fetched = Alert.get_by_id(alert.id)

    assert fetched.status == "firing"
    assert fetched.severity == "critical"
    assert fetched.labels["alertname"] == "DiskFull"
    assert fetched.annotations["summary"] == "Disk is full"
