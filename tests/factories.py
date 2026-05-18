from datetime import datetime, timedelta

from app.login import hash_password
from app.modules.db.models import (
    Alert,
    AlertRoute,
    AlertRouteChannel,
    Group,
    NotificationChannel,
    Rotation,
    RotationMember,
    RotationOverride,
    Silence,
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
    return Group.create(name=name, slug=slug, active=True)


def create_user(
    username: str | None = None,
    group: Group | None = None,
    *,
    email: str | None = None,
    is_admin: bool = False,
    active: bool = True,
) -> User:
    username = username or unique("user")
    email = email or f"{username}@example.com"

    user = User.create(
        username=username,
        display_name=username.title(),
        email=email,
        password_hash=hash_password("password-123"),
        active=active,
        is_admin=is_admin,
        active_group=group,
    )

    if group is not None:
        UserGroup.create(user=user, group=group, role="rw", active=True)

    return user


def create_team(group: Group, name: str | None = None, slug: str | None = None) -> Team:
    name = name or unique("Team")
    slug = slug or unique("team")
    return Team.create(group=group, name=name, slug=slug, active=True)


def add_user_to_team(team: Team, user: User, role: str = "rw") -> TeamUser:
    return TeamUser.create(team=team, user=user, role=role, active=True)


def create_rotation(
    team: Team,
    name: str | None = None,
    users: list[User] | None = None,
    *,
    start_at: datetime | None = None,
    duration_seconds: int = 86400,
) -> Rotation:
    rotation = Rotation.create(
        team=team,
        name=name or unique("Rotation"),
        description=None,
        start_at=start_at or datetime.utcnow().replace(microsecond=0),
        duration_seconds=duration_seconds,
        reminder_interval_seconds=300,
        rotation_type="daily",
        interval_value=1,
        interval_unit="days",
        handoff_time="09:00",
        timezone="UTC",
        enabled=True,
    )

    for index, user in enumerate(users or []):
        RotationMember.create(rotation=rotation, user=user, position=index, active=True)

    return rotation


def create_rotation_override(
    rotation: Rotation,
    user: User,
    *,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
) -> RotationOverride:
    starts_at = starts_at or datetime.utcnow() - timedelta(minutes=5)
    ends_at = ends_at or datetime.utcnow() + timedelta(minutes=5)
    return RotationOverride.create(
        rotation=rotation,
        user=user,
        starts_at=starts_at,
        ends_at=ends_at,
        reason="test override",
    )


def create_channel(
    group: Group,
    team: Team | None = None,
    *,
    channel_type: str = "webhook",
    config: dict | None = None,
) -> NotificationChannel:
    return NotificationChannel.create(
        group=group,
        team=team,
        name=unique("channel"),
        channel_type=channel_type,
        config=config or {"webhook_url": "https://example.com/webhook"},
        enabled=True,
    )


def create_route(
    team: Team,
    *,
    source: str = "alertmanager",
    token_hash: str | None = None,
    rotation: Rotation | None = None,
    matchers: dict | None = None,
    group_by: list[str] | None = None,
) -> AlertRoute:
    return AlertRoute.create(
        team=team,
        rotation=rotation,
        name=unique("route"),
        source=source,
        enabled=True,
        matchers=matchers or {},
        group_by=group_by or [],
        intake_token_prefix="test-prefix" if token_hash else None,
        intake_token_hash=token_hash,
    )


def attach_channel(route: AlertRoute, channel: NotificationChannel) -> AlertRouteChannel:
    return AlertRouteChannel.create(route=route, channel=channel)


def create_alert(route: AlertRoute, *, status: str = "firing") -> Alert:
    return Alert.create(
        team=route.team,
        route=route,
        rotation=route.rotation,
        source=route.source,
        external_id=unique("external"),
        dedup_key=unique("dedup"),
        group_key=unique("group"),
        title="DiskFull",
        message="/var is 95% full",
        severity="critical",
        labels={"alertname": "DiskFull", "instance": "host1", "team": route.team.slug},
        payload={"source": "test"},
        status=status,
    )


def create_silence(
    team: Team,
    *,
    matchers: dict | None = None,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
) -> Silence:
    return Silence.create(
        team=team,
        name=unique("silence"),
        reason="test silence",
        matchers=matchers or {},
        starts_at=starts_at or datetime.utcnow() - timedelta(minutes=5),
        ends_at=ends_at or datetime.utcnow() + timedelta(minutes=5),
        enabled=True,
    )
