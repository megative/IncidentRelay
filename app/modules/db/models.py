import json
from datetime import datetime

from peewee import (
    AutoField,
    BooleanField,
    CharField,
    DateTimeField,
    ForeignKeyField,
    IntegerField,
    Model,
    TextField,
)

from app.db import database_proxy


class JSONTextField(TextField):
    """Store JSON-compatible values in a portable text field."""

    def db_value(self, value):
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False)

    def python_value(self, value):
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except Exception:
            return value


class BaseModel(Model):
    """Base model for all tables."""

    class Meta:
        database = database_proxy


class SoftDeleteModel(BaseModel):
    """Base model for soft-deletable resources."""

    deleted = BooleanField(default=False, index=True)
    deleted_at = DateTimeField(null=True)


class Migration(BaseModel):
    """Applied migration record."""

    id = AutoField()
    name = CharField(unique=True)
    applied_at = DateTimeField(default=datetime.utcnow)


class MigrationState(BaseModel):
    """Legacy migration state record kept for backward compatibility."""

    id = AutoField()
    version = IntegerField(unique=True)
    name = CharField()
    service_version = CharField(null=True)
    applied_at = DateTimeField(default=datetime.utcnow)


class Group(SoftDeleteModel):
    """Access boundary for all resources."""

    id = AutoField()
    slug = CharField(unique=True)
    name = CharField()
    description = TextField(null=True)
    active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = "oncall_group"


class Team(SoftDeleteModel):
    """Independent on-call team inside a group."""

    id = AutoField()
    group = ForeignKeyField(Group, null=True, backref="teams", on_delete="CASCADE")
    slug = CharField(unique=True)
    name = CharField()
    description = TextField(null=True)
    escalation_enabled = BooleanField(default=True)
    escalation_after_reminders = IntegerField(default=2)
    active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)


class User(SoftDeleteModel):
    """On-call user."""

    id = AutoField()
    username = CharField(unique=True)
    display_name = CharField(null=True)
    email = CharField(null=True)
    phone = CharField(null=True)
    telegram_user_id = CharField(null=True)
    slack_user_id = CharField(null=True)
    mattermost_user_id = CharField(null=True)
    password_hash = CharField(null=True)
    active = BooleanField(default=True)
    is_admin = BooleanField(default=False)
    active_group = ForeignKeyField(Group, null=True, backref="active_users", on_delete="SET NULL")
    created_at = DateTimeField(default=datetime.utcnow)


class UserGroup(BaseModel):
    """User membership in a group.

    Role values:
    - viewer: can see group-scoped data;
    - editor: can create/edit group-level operational resources;
    - user_admin: can create and manage users only inside this group boundary.
    """

    id = AutoField()
    user = ForeignKeyField(User, backref="group_memberships", on_delete="CASCADE")
    group = ForeignKeyField(Group, backref="user_memberships", on_delete="CASCADE")
    role = CharField(default="viewer")
    active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        indexes = (
            (("user", "group"), True),
        )


class Role(BaseModel):
    """RBAC role placeholder."""

    id = AutoField()
    name = CharField(unique=True)
    description = TextField(null=True)
    permissions = JSONTextField(null=True)
    created_at = DateTimeField(default=datetime.utcnow)


class UserRole(BaseModel):
    """RBAC user role assignment placeholder."""

    id = AutoField()
    user = ForeignKeyField(User, backref="role_assignments", on_delete="CASCADE")
    role = ForeignKeyField(Role, backref="user_assignments", on_delete="CASCADE")
    team = ForeignKeyField(Team, null=True, backref="role_assignments", on_delete="CASCADE")
    created_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        indexes = (
            (("user", "role", "team"), True),
        )


class TeamUser(BaseModel):
    """Membership between teams and users.

    Role values:
    - viewer: can see team resources;
    - responder: can see team resources and ack/resolve alerts;
    - manager: can manage team resources and team membership.
    """

    id = AutoField()
    team = ForeignKeyField(Team, backref="memberships", on_delete="CASCADE")
    user = ForeignKeyField(User, backref="team_memberships", on_delete="CASCADE")
    role = CharField(default="viewer")
    active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        indexes = (
            (("team", "user"), True),
        )


class Rotation(SoftDeleteModel):
    """On-call rotation for a specific team."""

    id = AutoField()
    team = ForeignKeyField(Team, backref="rotations", on_delete="CASCADE")
    name = CharField()
    description = TextField(null=True)
    start_at = DateTimeField()
    duration_seconds = IntegerField(default=86400)
    reminder_interval_seconds = IntegerField(default=300)
    rotation_type = CharField(default="daily")
    interval_value = IntegerField(default=1)
    interval_unit = CharField(default="days")
    handoff_time = CharField(default="09:00")
    handoff_weekday = IntegerField(null=True)
    timezone = CharField(default="UTC")
    enabled = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = "rotation"


class RotationMember(BaseModel):
    """User position inside a rotation."""

    id = AutoField()
    rotation = ForeignKeyField(Rotation, backref="members", on_delete="CASCADE")
    user = ForeignKeyField(User, backref="rotation_memberships", on_delete="CASCADE")
    position = IntegerField()
    active = BooleanField(default=True)

    class Meta:
        indexes = (
            (("rotation", "position"), True),
            (("rotation", "user"), True),
        )


class RotationOverride(BaseModel):
    """Temporary override for a rotation."""

    id = AutoField()
    rotation = ForeignKeyField(Rotation, backref="overrides", on_delete="CASCADE")
    user = ForeignKeyField(User, backref="rotation_overrides", on_delete="CASCADE")
    starts_at = DateTimeField()
    ends_at = DateTimeField()
    reason = TextField(null=True)
    created_at = DateTimeField(default=datetime.utcnow)


class NotificationChannel(SoftDeleteModel):
    """Notification target."""

    id = AutoField()
    group = ForeignKeyField(Group, null=True, backref="channels", on_delete="CASCADE")
    team = ForeignKeyField(Team, backref="channels", null=True, on_delete="CASCADE")
    name = CharField()
    channel_type = CharField()
    config = JSONTextField(null=True)
    enabled = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        indexes = (
            (("team", "name"), True),
        )


class AlertRoute(SoftDeleteModel):
    """Route incoming alerts to a team, rotation and channels."""

    id = AutoField()
    team = ForeignKeyField(Team, backref="alert_routes", on_delete="CASCADE")
    name = CharField()
    source = CharField()
    rotation = ForeignKeyField(Rotation, backref="alert_routes", null=True, on_delete="SET NULL")
    matchers = JSONTextField(null=True)
    group_by = JSONTextField(null=True)
    intake_token_prefix = CharField(null=True, index=True)
    intake_token_hash = CharField(null=True)
    enabled = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        indexes = (
            (("team", "name"), True),
        )


class AlertRouteChannel(BaseModel):
    """Link an alert route to notification channels."""

    id = AutoField()
    route = ForeignKeyField(AlertRoute, backref="route_channels", on_delete="CASCADE")
    channel = ForeignKeyField(NotificationChannel, backref="channel_routes", on_delete="CASCADE")

    class Meta:
        indexes = (
            (("route", "channel"), True),
        )


class Alert(BaseModel):
    """Alert stored after normalization and routing."""

    id = AutoField()
    team = ForeignKeyField(Team, null=True, backref="alerts", on_delete="SET NULL")
    route = ForeignKeyField(AlertRoute, null=True, backref="alerts", on_delete="SET NULL")
    rotation = ForeignKeyField(Rotation, null=True, backref="alerts", on_delete="SET NULL")
    assignee = ForeignKeyField(User, null=True, backref="assigned_alerts", on_delete="SET NULL")
    source = CharField()
    external_id = CharField(null=True)
    dedup_key = CharField(index=True)
    group_key = CharField(index=True)
    title = CharField()
    message = TextField(null=True)
    severity = CharField(null=True)
    labels = JSONTextField(null=True)
    payload = JSONTextField(null=True)
    status = CharField(default="firing")
    previous_status = CharField(null=True)
    acknowledged_by = ForeignKeyField(User, null=True, backref="acknowledged_alerts", on_delete="SET NULL")
    acknowledged_at = DateTimeField(null=True)
    first_seen_at = DateTimeField(default=datetime.utcnow)
    last_seen_at = DateTimeField(default=datetime.utcnow)
    last_notification_at = DateTimeField(null=True)
    reminder_count = IntegerField(default=0)
    escalation_level = IntegerField(default=0)
    silenced = BooleanField(default=False)
    resolved_at = DateTimeField(null=True)

    class Meta:
        indexes = (
            (("team", "status"), False),
            (("source", "dedup_key"), False),
            (("group_key", "status"), False),
        )


class AlertEvent(BaseModel):
    """Alert history event."""

    id = AutoField()
    alert = ForeignKeyField(Alert, backref="events", on_delete="CASCADE")
    event_type = CharField()
    message = TextField(null=True)
    user = ForeignKeyField(User, null=True, backref="alert_events", on_delete="SET NULL")
    created_at = DateTimeField(default=datetime.utcnow)


class AlertNotification(BaseModel):
    """Delivery record for a notification sent to an external channel."""

    id = AutoField()
    alert = ForeignKeyField(Alert, backref="notifications", on_delete="CASCADE")
    channel = ForeignKeyField(NotificationChannel, backref="notifications", on_delete="CASCADE")
    provider = CharField()
    external_message_id = CharField(null=True)
    external_channel_id = CharField(null=True)
    last_event_type = CharField(null=True)
    last_error = TextField(null=True)
    provider_status = CharField(null=True)
    provider_payload = JSONTextField(null=True)
    last_callback_at = DateTimeField(null=True)
    callback_count = IntegerField(default=0)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        indexes = (
            (("alert", "channel"), True),
            (("channel", "external_message_id"), False),
        )


class AlertNotificationEvent(BaseModel):
    """Provider callback history for a notification delivery."""

    id = AutoField()
    notification = ForeignKeyField(
        AlertNotification,
        backref="callback_events",
        on_delete="CASCADE",
    )
    event_type = CharField()
    provider_status = CharField(null=True)
    digit = CharField(null=True)
    action = CharField(null=True)
    message = TextField(null=True)
    payload = JSONTextField(null=True)
    created_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        indexes = (
            (("notification", "created_at"), False),
        )


class Silence(SoftDeleteModel):
    """Alert silence rule for a team."""

    id = AutoField()
    team = ForeignKeyField(Team, backref="silences", on_delete="CASCADE")
    name = CharField()
    reason = TextField(null=True)
    matchers = JSONTextField(null=True)
    starts_at = DateTimeField()
    ends_at = DateTimeField()
    created_by = ForeignKeyField(User, null=True, backref="created_silences", on_delete="SET NULL")
    created_at = DateTimeField(default=datetime.utcnow)
    enabled = BooleanField(default=True)


class ApiToken(SoftDeleteModel):
    """Hashed API token."""

    id = AutoField()
    user = ForeignKeyField(User, null=True, backref="api_tokens", on_delete="CASCADE")
    group = ForeignKeyField(Group, null=True, backref="api_tokens", on_delete="CASCADE")
    team = ForeignKeyField(Team, null=True, backref="api_tokens", on_delete="CASCADE")
    name = CharField()
    token_prefix = CharField(index=True)
    token_hash = CharField(unique=True)
    scopes = JSONTextField(null=True)
    expires_at = DateTimeField(null=True)
    active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    last_used_at = DateTimeField(null=True)


class SsoProvider(SoftDeleteModel):
    """SSO provider configuration for OIDC or SAML."""

    id = AutoField()
    slug = CharField(unique=True)
    label = CharField()
    protocol = CharField(default="oidc", index=True)  # oidc | saml
    enabled = BooleanField(default=True)

    # Common mapping options
    subject_claim = CharField(default="sub")
    email_claim = CharField(default="email")
    username_claim = CharField(default="preferred_username")
    display_name_claim = CharField(default="name")
    groups_claim = CharField(default="groups")
    phone_claim = CharField(default="mobile")

    allowed_domains = JSONTextField(null=True)

    auto_create_users = BooleanField(default=False)
    auto_link_by_email = BooleanField(default=True)
    require_verified_email = BooleanField(default=True)

    sync_group_memberships = BooleanField(default=True)
    remove_missing_group_memberships = BooleanField(default=False)

    # OIDC
    client_id = CharField(null=True)
    client_secret_encrypted = TextField(null=True)
    oidc_metadata_url = TextField(null=True)
    oidc_issuer = TextField(null=True)
    oidc_authorization_endpoint = TextField(null=True)
    oidc_token_endpoint = TextField(null=True)
    oidc_userinfo_endpoint = TextField(null=True)
    oidc_jwks_uri = TextField(null=True)
    oidc_scope = CharField(default="openid email profile")

    # SAML IdP
    saml_idp_entity_id = TextField(null=True)
    saml_idp_sso_url = TextField(null=True)
    saml_idp_slo_url = TextField(null=True)
    saml_idp_x509_cert = TextField(null=True)
    saml_idp_metadata_url = CharField(null=True, max_length=2048)

    # SAML SP
    saml_sp_entity_id = TextField(null=True)
    saml_sp_acs_url = TextField(null=True)
    saml_sp_sls_url = TextField(null=True)
    saml_sp_x509_cert = TextField(null=True)
    saml_sp_private_key_encrypted = TextField(null=True)
    saml_name_id_format = TextField(
        default="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    )

    extra_config = JSONTextField(null=True)

    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = "sso_provider"


class SsoIdentity(BaseModel):
    """External SSO identity linked to local IncidentRelay user."""

    id = AutoField()
    user = ForeignKeyField(User, backref="sso_identities", on_delete="CASCADE")
    provider = ForeignKeyField(SsoProvider, backref="identities", on_delete="CASCADE")

    subject = CharField()
    email = CharField(null=True)
    username = CharField(null=True)

    raw_claims = JSONTextField(null=True)

    created_at = DateTimeField(default=datetime.utcnow)
    last_login_at = DateTimeField(null=True)

    class Meta:
        table_name = "sso_identity"
        indexes = (
            (("provider", "subject"), True),
        )


class SsoGroupMapping(BaseModel):
    """Map external SSO group value to IncidentRelay group role."""

    id = AutoField()
    provider = ForeignKeyField(SsoProvider, backref="group_mappings", on_delete="CASCADE")

    external_group = CharField()
    incidentrelay_group = ForeignKeyField(
        Group,
        backref="sso_group_mappings",
        on_delete="CASCADE",
    )

    group_role = CharField(default="viewer")
    active = BooleanField(default=True)
    priority = IntegerField(default=100)

    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = "sso_group_mapping"
        indexes = (
            (("provider", "external_group", "incidentrelay_group"), True),
        )


class AuditLog(BaseModel):
    """Audit log entry for API actions."""

    id = AutoField()
    group = ForeignKeyField(Group, null=True, backref="audit_logs", on_delete="SET NULL")
    team = ForeignKeyField(Team, null=True, backref="audit_logs", on_delete="SET NULL")
    user = ForeignKeyField(User, null=True, backref="audit_logs", on_delete="SET NULL")
    api_token = ForeignKeyField(ApiToken, null=True, backref="audit_logs", on_delete="SET NULL")
    action = CharField()
    object_type = CharField(null=True)
    object_id = IntegerField(null=True)
    message = TextField(null=True)
    data = JSONTextField(null=True)
    created_at = DateTimeField(default=datetime.utcnow)


class AppLock(BaseModel):
    """Distributed application lock stored in the database."""

    id = AutoField()
    name = CharField(unique=True)
    owner = CharField()
    expires_at = DateTimeField()
    updated_at = DateTimeField(default=datetime.utcnow)


class RotationLayer(SoftDeleteModel):
    """Schedule layer inside a rotation.

    Rotation stays the route-facing object.
    Layers define competing/overriding schedules inside it.
    Higher priority wins.
    """

    id = AutoField()
    rotation = ForeignKeyField(Rotation, backref="layers", on_delete="CASCADE")
    name = CharField()
    description = TextField(null=True)

    priority = IntegerField(default=0, index=True)

    start_at = DateTimeField(null=True)
    duration_seconds = IntegerField(null=True)

    rotation_type = CharField(null=True)
    interval_value = IntegerField(null=True)
    interval_unit = CharField(null=True)
    handoff_time = CharField(null=True)
    handoff_weekday = IntegerField(null=True)
    timezone = CharField(null=True)

    enabled = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = "rotation_layer"
        indexes = (
            (("rotation", "priority"), False),
        )


class RotationLayerMember(BaseModel):
    """User position inside a rotation layer."""

    id = AutoField()
    layer = ForeignKeyField(RotationLayer, backref="members", on_delete="CASCADE")
    user = ForeignKeyField(User, backref="rotation_layer_memberships", on_delete="CASCADE")
    position = IntegerField()
    active = BooleanField(default=True)

    class Meta:
        table_name = "rotation_layer_member"
        indexes = (
            (("layer", "position"), True),
            (("layer", "user"), True),
        )


class RotationLayerRestriction(BaseModel):
    """Local-time active window for a rotation layer.

    weekday: 0=Monday ... 6=Sunday, null means every day.
    start_time/end_time are local to the layer timezone or rotation timezone.
    """

    id = AutoField()
    layer = ForeignKeyField(RotationLayer, backref="restrictions", on_delete="CASCADE")
    weekday = IntegerField(null=True)
    start_time = CharField()
    end_time = CharField()
    created_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = "rotation_layer_restriction"
        indexes = (
            (("layer", "weekday"), False),
        )
