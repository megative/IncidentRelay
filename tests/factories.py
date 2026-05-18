from datetime import datetime, timedelta, timezone

from app.login import hash_password
from app.modules.db.models import (
    Alert,
    AlertRoute,
    AlertRouteChannel,
    Group,
    NotificationChannel,
    Rotation,
    RotationMember,
    Team,
    TeamUser,
    User,
    UserGroup,
)


_counter = 0


def unique(prefix: str) -> str:
    global _counter
    _counter += 1
    return f"{prefix}-{_counter}"


def create_group(name: str | None = None, slug: str | None = None) -> Group:
    name = name or unique("Group")
    slug = slug or unique("group")
    return Group.create(name=name, slug=slug, is_active=True)


def create_user(
    username: str | None = None,
    group: Group | None = None,
    *,
    email: str | None = None,
    is_admin: bool = False,
    is_active: bool = True,
) -> User:
    username = username or unique("user")
    email = email or f"{username}@example.com"
    user = User.create(
        username=username,
        email=email,
        password_hash=hash_password("password-123"),
        full_name=username.title(),
        is_admin=is_admin,
        is_active=is_active,
        active_group=group,
    )

    if group is not None:
        UserGroup.create(user=user, group=group)

    return user


def create_team(group: Group, name: str | None = None, slug: str | None = None) -> Team:
    name = name or unique("Team")
    slug = slug or unique("team")
    return Team.create(group=group, name=name, slug=slug, is_active=True)


def add_user_to_team(team: Team, user: User) -> TeamUser:
    return TeamUser.create(team=team, user=user)


def create_rotation(team: Team, name: str | None = None, users: list[User] | None = None) -> Rotation:
    rotation = Rotation.create(
        team=team,
        name=name or unique("Rotation"),
        timezone="UTC",
        starts_at=datetime.now(timezone.utc),
        handoff_time="09:00",
        shift_duration_hours=24,
        is_active=True,
    )

    for index, user in enumerate(users or []):
        RotationMember.create(rotation=rotation, user=user, position=index)

    return rotation


def create_channel(
    group: Group,
    *,
    channel_type: str = "webhook",
    config: dict | None = None,
) -> NotificationChannel:
    return NotificationChannel.create(
        group=group,
        name=unique("channel"),
        type=channel_type,
        config=config or {"url": "https://example.com/webhook"},
        is_enabled=True,
    )


def create_route(
    group: Group,
    team: Team,
    *,
    token_hash: str | None = None,
    rotation: Rotation | None = None,
) -> AlertRoute:
    return AlertRoute.create(
        group=group,
        team=team,
        rotation=rotation,
        name=unique("route"),
        source="alertmanager",
        enabled=True,
        matchers={},
        group_by=["alertname", "instance"],
        intake_token_prefix="test-prefix",
        intake_token_hash=token_hash,
    )


def attach_channel(route: AlertRoute, channel: NotificationChannel) -> AlertRouteChannel:
    return AlertRouteChannel.create(route=route, channel=channel)


def create_alert(route: AlertRoute, *, status: str = "firing") -> Alert:
    return Alert.create(
        route=route,
        dedup_key=unique("dedup"),
        fingerprint=unique("fingerprint"),
        source="alertmanager",
        status=status,
        severity="critical",
        title="DiskFull",
        message="/var is 95% full",
        labels={"alertname": "DiskFull", "instance": "host1"},
        annotations={"summary": "Disk is full"},
        starts_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
