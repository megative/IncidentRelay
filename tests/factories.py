from datetime import datetime, timedelta

from app.login import hash_password
from app.modules.db import rotations_repo
from app.modules.db.models import (
    Alert,
    AlertRoute,
    AlertRouteChannel,
    Group,
    NotificationChannel,
    Rotation,
    RotationOverride,
    Silence,
    Team,
    TeamUser,
    User,
    UserGroup,
    EscalationPolicy,
    EscalationPolicyRule,
    Service
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


_DEFAULT_EMAIL = object()


def create_user(
    username: str | None = None,
    group: Group | None = None,
    *,
    email: str | None | object = _DEFAULT_EMAIL,
    is_admin: bool = False,
    active: bool = True,
    group_role: str = "editor",
) -> User:
    username = username or unique("user")

    if email is _DEFAULT_EMAIL:
        email = f"{username}@example.com"

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
        UserGroup.create(
            user=user,
            group=group,
            role=group_role,
            active=True,
        )

    return user


def create_team(group: Group, name: str | None = None, slug: str | None = None) -> Team:
    name = name or unique("Team")
    slug = slug or unique("team")
    return Team.create(group=group, name=name, slug=slug, active=True)


def add_user_to_team(team: Team, user: User, role: str = "manager") -> TeamUser:
    return TeamUser.create(team=team, user=user, role=role, active=True)


def create_rotation(
    team: Team,
    name: str | None = None,
    users: list[User] | None = None,
    *,
    start_at: datetime | None = None,
    duration_seconds: int = 86400,
) -> Rotation:
    rotation = rotations_repo.create_rotation(
        team_id=team.id,
        name=name or unique("Rotation"),
        description=None,
        start_at=start_at or datetime.utcnow().replace(microsecond=0),
        duration_seconds=duration_seconds,
        reminder_interval_seconds=300,
        rotation_type="daily",
        interval_value=1,
        interval_unit="days",
        handoff_time="09:00",
        handoff_weekday=None,
        timezone="UTC",
        enabled=True,
    )

    layer = rotations_repo.get_or_create_default_layer(rotation.id)

    for index, user in enumerate(users or []):
        rotations_repo.add_rotation_layer_member(
            layer_id=layer.id,
            user_id=user.id,
            position=index,
        )

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
        config=(
            {"webhook_url": ""}
            if config is None
            else config
        ),
        enabled=True,
    )


def create_route(
    team: Team,
    *,
    name: str | None = None,
    source: str = "alertmanager",
    token_hash: str | None = None,
    rotation: Rotation | None = None,
    escalation_policy=None,
    matchers: dict | None = None,
    group_by: list[str] | None = None,
    service: Service | None = None,
) -> AlertRoute:
    return AlertRoute.create(
        team=team,
        rotation=rotation,
        escalation_policy=escalation_policy,
        name=name or unique("route"),
        source=source,
        enabled=True,
        matchers=matchers or {},
        group_by=group_by or [],
        intake_token_prefix="test-prefix" if token_hash else None,
        intake_token_hash=token_hash,
        service=service,
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


def create_escalation_policy(
    team: Team,
    *,
    name: str | None = None,
    description: str | None = None,
    enabled: bool = True,
    repeat_count: int = 0,
) -> EscalationPolicy:
    return EscalationPolicy.create(
        team=team,
        name=name or unique("policy"),
        description=description,
        enabled=enabled,
        repeat_count=repeat_count,
    )


def create_escalation_policy_rule(
    policy: EscalationPolicy,
    *,
    position: int = 1,
    delay_seconds: int = 60,
    target_type: str = "rotation",
    rotation: Rotation | None = None,
    user: User | None = None,
    enabled: bool = True,
) -> EscalationPolicyRule:
    return EscalationPolicyRule.create(
        policy=policy,
        position=position,
        delay_seconds=delay_seconds,
        target_type=target_type,
        target_rotation=rotation if target_type == "rotation" else None,
        target_user=user if target_type == "user" else None,
        enabled=enabled,
    )


def create_service(
    team: Team,
    name: str | None = None,
    slug: str | None = None,
    *,
    service_type: str = "other",
    environment: str = "production",
    criticality: str = "medium",
    tier: str = "tier_3",
    status: str = "operational",
    enabled: bool = True,
) -> Service:
    service_name = name or unique("Service")
    service_slug = slug or unique("service")

    return Service.create(
        group=team.group,
        team=team,
        slug=service_slug,
        name=service_name,
        service_type=service_type,
        environment=environment,
        criticality=criticality,
        tier=tier,
        status=status,
        status_source="manual",
        labels={},
        tags=[],
        metadata={},
        enabled=enabled,
        public=False,
        public_order=100,
    )
