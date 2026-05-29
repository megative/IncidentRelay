from datetime import datetime, timezone

from app.modules.sso.saml_security import get_saml_security


def serialize_utc_datetime(value):
    """Serialize a datetime as an explicit UTC ISO-8601 string."""
    if not value:
        return None

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)

    return value.isoformat().replace("+00:00", "Z")


def attach_group_permissions(data, group_id, current_user=None):
    """Attach group permissions to serialized data."""
    if current_user and group_id:
        from app.services.rbac import get_group_permissions

        data["permissions"] = get_group_permissions(current_user, group_id)

    return data


def attach_team_permissions(data, team_id, current_user=None):
    """Attach team permissions to serialized data."""
    if current_user and team_id:
        from app.services.rbac import get_team_permissions

        data["permissions"] = get_team_permissions(current_user, team_id)

    return data


def serialize_group(group, current_user=None):
    """
    Serialize a group.
    """

    data = {
        "id": group.id,
        "slug": group.slug,
        "name": group.name,
        "description": group.description,
        "active": group.active,
    }

    return attach_group_permissions(data, group.id, current_user)


def serialize_user_group(membership):
    """
    Serialize a group membership.
    """

    return {
        "id": membership.id,
        "group_id": membership.group.id,
        "group_slug": membership.group.slug,
        "group_name": membership.group.name,
        "role": membership.role,
        "active": membership.active,
    }


def serialize_team(team, current_user=None):
    """
    Serialize a team.
    """

    data = {
        "id": team.id,
        "group_id": team.group.id if team.group else None,
        "group_slug": team.group.slug if team.group else None,
        "group_name": team.group.name if team.group else None,
        "slug": team.slug,
        "name": team.name,
        "description": team.description,
        "escalation_enabled": team.escalation_enabled,
        "escalation_after_reminders": team.escalation_after_reminders,
        "active": team.active,
    }

    return attach_team_permissions(data, team.id, current_user)


def serialize_user(user, groups=None):
    """
    Serialize a user.
    """

    data = {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "email": user.email,
        "phone": user.phone,
        "telegram_user_id": user.telegram_user_id,
        "slack_user_id": user.slack_user_id,
        "mattermost_user_id": user.mattermost_user_id,
        "active": user.active,
        "is_admin": user.is_admin,
        "active_group_id": user.active_group.id if user.active_group else None,
        "active_group_slug": user.active_group.slug if user.active_group else None,
    }

    if groups is not None:
        data["groups"] = [serialize_profile_group(item) for item in groups]

    return data


def serialize_user_short(user):
    """
    Serialize a compact user object.
    """

    if not user:
        return None

    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "email": user.email,
        "telegram_user_id": user.telegram_user_id,
        "slack_user_id": user.slack_user_id,
        "mattermost_user_id": user.mattermost_user_id,
    }


def serialize_rotation(rotation, current_user=None, request_user=None):
    """Serialize a rotation.

    current_user is the current on-call user.
    request_user is the authenticated user used for permissions.
    """
    data = {
        "id": rotation.id,
        "team_id": rotation.team.id,
        "team_slug": rotation.team.slug,
        "name": rotation.name,
        "description": rotation.description,
        "start_at": rotation.start_at.isoformat(),
        "duration_seconds": rotation.duration_seconds,
        "reminder_interval_seconds": rotation.reminder_interval_seconds,
        "rotation_type": rotation.rotation_type,
        "interval_value": rotation.interval_value,
        "interval_unit": rotation.interval_unit,
        "handoff_time": rotation.handoff_time,
        "handoff_weekday": rotation.handoff_weekday,
        "timezone": rotation.timezone,
        "enabled": rotation.enabled,
        "current_oncall": current_user.username if current_user else None,
    }

    return attach_team_permissions(data, rotation.team.id, request_user)


def serialize_channel(channel, current_user=None):
    """Serialize a notification channel."""
    team_id = channel.team.id if channel.team else None

    data = {
        "id": channel.id,
        "group_id": channel.group.id if getattr(channel, "group", None) else None,
        "group_slug": channel.group.slug if getattr(channel, "group", None) else None,
        "team_id": team_id,
        "team_slug": channel.team.slug if channel.team else None,
        "name": channel.name,
        "channel_type": channel.channel_type,
        "config": channel.config,
        "enabled": channel.enabled,
    }

    return attach_team_permissions(data, team_id, current_user)


def serialize_channel_short(channel):
    """
    Serialize a compact channel object.
    """

    if not channel:
        return None

    return {
        "id": channel.id,
        "name": channel.name,
        "channel_type": channel.channel_type,
        "enabled": channel.enabled,
    }


def serialize_service_short(service):
    """Serialize a compact service object."""
    if not service:
        return None

    return {
        "id": service.id,
        "slug": service.slug,
        "name": service.name,
        "status": service.status,
        "criticality": service.criticality,
        "environment": service.environment,
        "enabled": service.enabled,
    }


def serialize_service(service, current_user=None):
    """Serialize a service."""
    team = service.team if service.team_id else None
    group = service.group if service.group_id else None

    data = {
        "id": service.id,
        "group_id": group.id if group else None,
        "group_slug": group.slug if group else None,
        "group_name": group.name if group else None,
        "team_id": team.id if team else None,
        "team_slug": team.slug if team else None,
        "team_name": team.name if team else None,

        "slug": service.slug,
        "name": service.name,
        "description": service.description,

        "service_type": service.service_type,
        "environment": service.environment,
        "criticality": service.criticality,
        "tier": service.tier,

        "status": service.status,
        "status_source": service.status_source,
        "status_message": service.status_message,
        "status_updated_at": serialize_utc_datetime(service.status_updated_at),

        "default_rotation_id": (
            service.default_rotation.id
            if getattr(service, "default_rotation_id", None)
            else None
        ),
        "default_rotation_name": (
            service.default_rotation.name
            if getattr(service, "default_rotation_id", None)
            else None
        ),
        "default_escalation_policy_id": (
            service.default_escalation_policy.id
            if getattr(service, "default_escalation_policy_id", None)
            else None
        ),
        "default_escalation_policy_name": (
            service.default_escalation_policy.name
            if getattr(service, "default_escalation_policy_id", None)
            else None
        ),

        "labels": service.labels or {},
        "tags": service.tags or [],
        "metadata": service.metadata or {},

        "enabled": service.enabled,
        "public": service.public,
        "public_name": service.public_name,
        "public_description": service.public_description,
        "public_order": service.public_order,

        "created_at": serialize_utc_datetime(service.created_at),
        "updated_at": serialize_utc_datetime(service.updated_at),
    }

    return attach_team_permissions(data, service.team_id, current_user)


def serialize_service_match_rule(rule, current_user=None):
    """Serialize a service match rule."""
    service = rule.service if rule.service_id else None
    route = rule.route if getattr(rule, "route_id", None) else None
    team = rule.team if rule.team_id else None

    data = {
        "id": rule.id,
        "team_id": team.id if team else None,
        "team_slug": team.slug if team else None,
        "team_name": team.name if team else None,

        "route_id": route.id if route else None,
        "route_name": route.name if route else None,

        "service_id": service.id if service else None,
        "service_slug": service.slug if service else None,
        "service_name": service.name if service else None,

        "position": rule.position,
        "name": rule.name,
        "description": rule.description,
        "matchers": rule.matchers or {},
        "enabled": rule.enabled,

        "created_at": serialize_utc_datetime(rule.created_at),
        "updated_at": serialize_utc_datetime(rule.updated_at),
    }

    return attach_team_permissions(data, rule.team_id, current_user)


def serialize_route(route, current_user=None):
    """
    Serialize an alert route.
    """

    channels = [serialize_channel_short(link.channel) for link in route.route_channels]

    data = {
        "id": route.id,
        "team_id": route.team.id,
        "team_slug": route.team.slug,
        "name": route.name,
        "source": route.source,
        "rotation_id": route.rotation.id if route.rotation else None,
        "rotation_name": route.rotation.name if route.rotation else None,
        "escalation_policy_id": route.escalation_policy.id if route.escalation_policy else None,
        "escalation_policy_name": route.escalation_policy.name if route.escalation_policy else None,
        "escalation_mode": "policy" if route.escalation_policy else "rotation",
        "team_escalation_enabled": route.team.escalation_enabled if route.team else None,
        "team_escalation_after_reminders": (
            route.team.escalation_after_reminders if route.team else None
        ),
        "matchers": route.matchers,
        "group_by": route.group_by,
        "enabled": route.enabled,
        "intake_token_prefix": route.intake_token_prefix,
        "has_intake_token": bool(route.intake_token_hash),
        "channels": channels,
        "service_id": route.service.id if getattr(route, "service_id", None) else None,
        "service_name": route.service.name if getattr(route, "service_id", None) else None,
        "service_slug": route.service.slug if getattr(route, "service_id", None) else None,
    }

    return attach_team_permissions(data, route.team.id, current_user)


def serialize_alert_event(event):
    """
    Serialize an alert event.
    """

    return {
        "id": event.id,
        "event_type": event.event_type,
        "message": event.message,
        "user": serialize_user_short(event.user),
        "created_at": event.created_at.isoformat(),
    }


def serialize_alert_notification(notification):
    """
    Serialize an alert notification delivery record.
    """

    return {
        "id": notification.id,
        "channel": serialize_channel_short(notification.channel),
        "provider": notification.provider,
        "external_message_id": notification.external_message_id,
        "external_channel_id": notification.external_channel_id,
        "last_event_type": notification.last_event_type,
        "last_error": notification.last_error,
        "created_at": notification.created_at.isoformat(),
        "updated_at": notification.updated_at.isoformat(),
    }


def serialize_alert(
    alert,
    include_payload=False,
    include_details=False,
    events=None,
    notifications=None,
    current_user=None,
):
    """
    Serialize an alert.
    """

    team = alert.team
    route = alert.route
    rotation = alert.rotation
    service = alert.service if getattr(alert, "service_id", None) else None
    escalation_policy = (
        alert.escalation_policy
        if getattr(alert, "escalation_policy_id", None)
        else None
    )
    escalation_rule = (
        alert.escalation_rule
        if getattr(alert, "escalation_rule_id", None)
        else None
    )

    data = {
        "id": alert.id,
        "team_id": team.id if team else None,
        "team_slug": team.slug if team else None,
        "team_name": team.name if team else None,
        "route_id": route.id if route else None,
        "route_name": route.name if route else None,
        "route_source": route.source if route else None,
        "rotation_id": rotation.id if rotation else None,
        "rotation_name": rotation.name if rotation else None,
        "rotation_reminder_interval_seconds": rotation.reminder_interval_seconds if rotation else None,
        "source": alert.source,
        "external_id": alert.external_id,
        "dedup_key": alert.dedup_key,
        "group_key": alert.group_key,
        "title": alert.title,
        "message": alert.message,
        "severity": alert.severity,
        "status": alert.status,
        "previous_status": alert.previous_status,
        "silenced": alert.silenced,
        "labels": alert.labels or {},
        "labels_count": len(alert.labels or {}),
        "assignee": alert.assignee.username if alert.assignee else None,
        "assignee_id": alert.assignee.id if alert.assignee else None,
        "assignee_details": serialize_user_short(alert.assignee),
        "acknowledged_by": alert.acknowledged_by.username if alert.acknowledged_by else None,
        "acknowledged_by_details": serialize_user_short(alert.acknowledged_by),
        "acknowledged_at": serialize_utc_datetime(alert.acknowledged_at),
        "first_seen_at": serialize_utc_datetime(alert.first_seen_at),
        "last_seen_at": serialize_utc_datetime(alert.last_seen_at),
        "last_notification_at": serialize_utc_datetime(alert.last_notification_at),
        "reminder_count": alert.reminder_count,
        "escalation_level": alert.escalation_level,
        "escalation_mode": "policy" if escalation_policy else "rotation",
        "escalation_policy_id": escalation_policy.id if escalation_policy else None,
        "escalation_policy_name": escalation_policy.name if escalation_policy else None,
        "escalation_rule_id": escalation_rule.id if escalation_rule else None,
        "escalation_rule_position": escalation_rule.position if escalation_rule else None,
        "escalation_rule_target_type": escalation_rule.target_type if escalation_rule else None,
        "next_escalation_at": serialize_utc_datetime(getattr(alert, "next_escalation_at", None)),
        "last_escalated_at": serialize_utc_datetime(getattr(alert, "last_escalated_at", None)),
        "escalation_repeat_count": getattr(alert, "escalation_repeat_count", 0),
        "team_escalation_enabled": team.escalation_enabled if team else None,
        "team_escalation_after_reminders": (team.escalation_after_reminders if team else None),
        "resolved_at": serialize_utc_datetime(alert.resolved_at),
        "service_id": service.id if service else None,
        "service_slug": service.slug if service else None,
        "service_name": service.name if service else None,
        "service_status": service.status if service else None,
        "service_criticality": service.criticality if service else None,
        "service_environment": service.environment if service else None,
        "service": serialize_service_short(service),
        "service_tier": service.tier if service else None,
    }

    if route:
        data["route"] = {
            "id": route.id,
            "name": route.name,
            "source": route.source,
            "matchers": route.matchers,
            "group_by": route.group_by,
            "enabled": route.enabled,
        }
        data["route"]["escalation_policy_id"] = (
            route.escalation_policy.id if getattr(route, "escalation_policy_id", None) else None
        )
        data["route"]["escalation_policy_name"] = (
            route.escalation_policy.name if getattr(route, "escalation_policy_id", None) else None
        )
        data["route"]["escalation_mode"] = (
            "policy" if getattr(route, "escalation_policy_id", None) else "rotation"
        )
        data["route"]["service_id"] = (
            route.service.id if getattr(route, "service_id", None) else None
        )
        data["route"]["service_name"] = (
            route.service.name if getattr(route, "service_id", None) else None
        )
        data["route"]["service_slug"] = (
            route.service.slug if getattr(route, "service_id", None) else None
        )

    if service:
        data["service"] = {
            "id": service.id,
            "name": service.name,
            "slug": service.slug,
            "status": service.status,
            "criticality": service.criticality,
            "environment": service.environment,
            "tier": service.tier,
            "enabled": service.enabled,
            "team_id": service.team.id if service.team else None,
            "team_slug": service.team.slug if service.team else None,
            "team_name": service.team.name if service.team else None,
        }

    if rotation:
        data["rotation"] = {
            "id": rotation.id,
            "name": rotation.name,
            "duration_seconds": rotation.duration_seconds,
            "reminder_interval_seconds": rotation.reminder_interval_seconds,
            "rotation_type": rotation.rotation_type,
            "interval_value": rotation.interval_value,
            "interval_unit": rotation.interval_unit,
            "handoff_time": rotation.handoff_time,
            "timezone": rotation.timezone,
            "enabled": rotation.enabled,
        }

    if include_payload:
        data["payload"] = alert.payload

    if include_details:
        data["events"] = [serialize_alert_event(event) for event in events or []]
        data["notifications"] = [
            serialize_alert_notification(item)
            for item in notifications or []
        ]

    return attach_team_permissions(data, team.id if team else None, current_user)


def serialize_api_token(token):
    """
    Serialize API token metadata.

    Never expose token_hash or full raw token.
    """
    expires_at = token.expires_at
    expired = bool(expires_at and expires_at <= datetime.utcnow())

    return {
        "id": token.id,
        "name": token.name,
        "token_prefix": token.token_prefix,
        "scopes": token.scopes or [],
        "group_id": token.group.id if token.group else None,
        "group_slug": token.group.slug if token.group else None,
        "group_name": token.group.name if token.group else None,
        "team_id": token.team.id if token.team else None,
        "team_slug": token.team.slug if token.team else None,
        "active": token.active,
        "expired": expired,
        "created_at": token.created_at.isoformat() if token.created_at else None,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "last_used_at": token.last_used_at.isoformat() if token.last_used_at else None,
    }


def serialize_profile_group(item):
    """Serialize a real UserGroup membership or a synthetic profile group."""
    if isinstance(item, dict):
        return item

    return serialize_user_group(item)


def serialize_rotation_layer(layer, current_user=None):
    """Serialize a rotation layer."""
    team_id = layer.rotation.team.id

    data = {
        "id": layer.id,
        "rotation_id": layer.rotation.id,
        "team_id": team_id,
        "name": layer.name,
        "description": layer.description,
        "priority": layer.priority,
        "start_at": layer.start_at.isoformat() if layer.start_at else None,
        "duration_seconds": layer.duration_seconds,
        "rotation_type": layer.rotation_type,
        "interval_value": layer.interval_value,
        "interval_unit": layer.interval_unit,
        "handoff_time": layer.handoff_time,
        "handoff_weekday": layer.handoff_weekday,
        "timezone": layer.timezone,
        "enabled": layer.enabled,
        "deleted": layer.deleted,
    }

    return attach_team_permissions(data, team_id, current_user)


def serialize_rotation_layer_member(member):
    """Serialize a rotation layer member."""
    return {
        "id": member.id,
        "layer_id": member.layer.id,
        "user_id": member.user.id,
        "username": member.user.username,
        "display_name": member.user.display_name,
        "position": member.position,
        "active": member.active,
    }


def serialize_rotation_layer_restriction(item):
    """Serialize a rotation layer restriction."""
    return {
        "id": item.id,
        "layer_id": item.layer.id,
        "weekday": item.weekday,
        "start_time": item.start_time,
        "end_time": item.end_time,
    }


def serialize_sso_provider(provider):
    """Serialize SSO provider without secrets."""
    return {
        "id": provider.id,
        "slug": provider.slug,
        "label": provider.label,
        "protocol": provider.protocol,
        "enabled": provider.enabled,

        "subject_claim": provider.subject_claim,
        "email_claim": provider.email_claim,
        "username_claim": provider.username_claim,
        "display_name_claim": provider.display_name_claim,
        "groups_claim": provider.groups_claim,
        "phone_claim": provider.phone_claim,

        "allowed_domains": provider.allowed_domains or [],

        "auto_create_users": provider.auto_create_users,
        "auto_link_by_email": provider.auto_link_by_email,
        "require_verified_email": provider.require_verified_email,

        "sync_group_memberships": provider.sync_group_memberships,
        "remove_missing_group_memberships": provider.remove_missing_group_memberships,

        "client_id": provider.client_id,
        "has_client_secret": bool(provider.client_secret_encrypted),

        "oidc_metadata_url": provider.oidc_metadata_url,
        "oidc_issuer": provider.oidc_issuer,
        "oidc_authorization_endpoint": provider.oidc_authorization_endpoint,
        "oidc_token_endpoint": provider.oidc_token_endpoint,
        "oidc_userinfo_endpoint": provider.oidc_userinfo_endpoint,
        "oidc_jwks_uri": provider.oidc_jwks_uri,
        "oidc_scope": provider.oidc_scope,

        "saml_idp_entity_id": provider.saml_idp_entity_id,
        "saml_idp_sso_url": provider.saml_idp_sso_url,
        "saml_idp_slo_url": provider.saml_idp_slo_url,
        "saml_idp_x509_cert": provider.saml_idp_x509_cert,
        "saml_idp_metadata_url": provider.saml_idp_metadata_url,

        "saml_sp_entity_id": provider.saml_sp_entity_id,
        "saml_sp_acs_url": provider.saml_sp_acs_url,
        "saml_sp_sls_url": provider.saml_sp_sls_url,
        "saml_sp_x509_cert": provider.saml_sp_x509_cert,
        "has_saml_sp_private_key": bool(provider.saml_sp_private_key_encrypted),
        "saml_name_id_format": provider.saml_name_id_format,

        "extra_config": provider.extra_config or {},
        "saml_security": get_saml_security(provider.extra_config),

        "created_at": provider.created_at.isoformat() if provider.created_at else None,
        "updated_at": provider.updated_at.isoformat() if provider.updated_at else None,
    }


def serialize_sso_group_mapping(mapping):
    """Serialize SSO group mapping."""
    group = mapping.incidentrelay_group

    return {
        "id": mapping.id,
        "provider_id": mapping.provider.id,
        "external_group": mapping.external_group,
        "group_id": group.id,
        "group_slug": group.slug,
        "group_name": group.name,
        "group_role": mapping.group_role,
        "active": mapping.active,
        "priority": mapping.priority,
        "created_at": mapping.created_at.isoformat() if mapping.created_at else None,
        "updated_at": mapping.updated_at.isoformat() if mapping.updated_at else None,
    }


def serialize_service_link(link, current_user=None):
    """Serialize a service link."""
    service = link.service
    team = service.team if service else None

    data = {
        "id": link.id,

        "service_id": service.id if service else link.service_id,
        "service_name": service.name if service else None,
        "service_slug": service.slug if service else None,

        "team_id": team.id if team else None,
        "team_name": team.name if team else None,
        "team_slug": team.slug if team else None,

        "link_type": link.link_type,
        "label": link.label,
        "url": link.url,
        "description": link.description,
        "priority": link.priority,
        "enabled": link.enabled,
        "created_at": serialize_utc_datetime(link.created_at),
        "updated_at": serialize_utc_datetime(link.updated_at),
    }

    return attach_team_permissions(
        data,
        team.id if team else None,
        current_user,
    )


def serialize_service_runbook(runbook, current_user=None):
    """Serialize a service runbook."""
    service = runbook.service
    team = service.team if service else None

    data = {
        "id": runbook.id,

        "service_id": service.id if service else runbook.service_id,
        "service_name": service.name if service else None,
        "service_slug": service.slug if service else None,

        "team_id": team.id if team else None,
        "team_name": team.name if team else None,
        "team_slug": team.slug if team else None,

        "title": runbook.title,
        "description": runbook.description,
        "url": runbook.url,
        "severity": runbook.severity,
        "matchers": runbook.matchers or {},
        "priority": runbook.priority,
        "enabled": runbook.enabled,
        "created_at": serialize_utc_datetime(runbook.created_at),
        "updated_at": serialize_utc_datetime(runbook.updated_at),
    }

    return attach_team_permissions(
        data,
        team.id if team else None,
        current_user,
    )


def serialize_service_dependency(dependency, current_user=None):
    """Serialize a service dependency."""
    service = dependency.service
    depends_on = dependency.depends_on_service

    data = {
        "id": dependency.id,

        "service_id": service.id,
        "service_name": service.name,
        "service_slug": service.slug,
        "team_id": service.team.id if service.team else None,
        "team_name": service.team.name if service.team else None,
        "team_slug": service.team.slug if service.team else None,

        "depends_on_service_id": depends_on.id,
        "depends_on_service_name": depends_on.name,
        "depends_on_service_slug": depends_on.slug,
        "depends_on_service_status": depends_on.status,

        "depends_on_team_id": depends_on.team.id if depends_on.team else None,
        "depends_on_team_name": depends_on.team.name if depends_on.team else None,
        "depends_on_team_slug": depends_on.team.slug if depends_on.team else None,

        "dependency_type": dependency.dependency_type,
        "criticality": dependency.criticality,
        "description": dependency.description,
        "enabled": dependency.enabled,
        "created_at": serialize_utc_datetime(dependency.created_at),
        "updated_at": serialize_utc_datetime(dependency.updated_at),
    }

    return attach_team_permissions(data, service.team_id, current_user)
