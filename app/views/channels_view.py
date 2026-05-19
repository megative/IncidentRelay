from types import SimpleNamespace

from flask import Blueprint, jsonify, request
from peewee import IntegrityError

from app.api.schemas.channels import ChannelCreateSchema, ChannelUpdateSchema
from app.modules.db import channels_repo, teams_repo
from app.notifiers.registry import get_notifier
from app.notifiers.voice.loader import list_voice_providers
from app.services.audit import write_audit
from app.services.rbac import get_allowed_team_ids, require_team_read, require_team_write
from app.services.serializers import serialize_channel
from app.services.validation import validate_body

channels_bp = Blueprint("channels_api", __name__)

CHANNEL_TYPES = [
    "telegram",
    "slack",
    "mattermost",
    "webhook",
    "discord",
    "teams",
    "email",
    "voice_call",
]


def channel_name_conflict_response(name):
    """Return a consistent conflict response for duplicate channel names."""
    return jsonify({
        "error": "conflict",
        "message": "Channel with this name already exists in this team",
        "details": [
            {
                "field": "name",
                "loc": ["name"],
                "message": "Channel name must be unique within a team",
                "type": "unique",
                "input": name,
            }
        ],
    }), 409


def is_channel_name_unique_violation(exc):
    """Return True when IntegrityError is caused by channel name uniqueness."""
    message = str(exc)
    return (
        "notificationchannel_team_id_name" in message
        or "notification_channel_team_id_name" in message
        or "team_id, name" in message
    )


def has_channel_name_conflict(team_id, name, *, exclude_channel_id=None):
    """Check whether a channel name is already used in this team."""
    return channels_repo.get_channel_by_team_and_name(
        team_id,
        name,
        exclude_channel_id=exclude_channel_id,
        include_deleted=True,
    ) is not None


def build_test_assignee(channel):
    """Return a fake assignee for channel tests that require profile contacts."""
    if channel.channel_type != "email":
        return None

    current_user = request.current_user
    return SimpleNamespace(
        id=getattr(current_user, "id", None),
        username=getattr(current_user, "username", "test-user"),
        display_name=getattr(current_user, "display_name", None),
        email=getattr(current_user, "email", None),
        phone=getattr(current_user, "phone", None),
    )


@channels_bp.route("/types", methods=["GET"])
def list_channel_types():
    """Return supported channel types."""
    return jsonify(CHANNEL_TYPES)


@channels_bp.route("", methods=["GET"])
def list_channels():
    """Return channels."""
    team_id = request.args.get("team_id", type=int)

    if team_id:
        error = require_team_read(team_id)
        if error:
            return error
        channels = channels_repo.list_channels(team_id=team_id)
    else:
        channels = channels_repo.list_channels(team_ids=get_allowed_team_ids())

    return jsonify([serialize_channel(channel) for channel in channels])


@channels_bp.route("/<int:channel_id>", methods=["GET"])
def get_channel(channel_id):
    """Return a single channel."""
    channel = channels_repo.get_channel(channel_id)

    if channel.team_id:
        error = require_team_read(channel.team_id)
        if error:
            return error

    return jsonify(serialize_channel(channel))


@channels_bp.route("", methods=["POST"])
def create_channel():
    """Create a notification channel."""
    payload, error = validate_body(ChannelCreateSchema)
    if error:
        return error

    error = require_team_write(payload.team_id)
    if error:
        return error

    if has_channel_name_conflict(payload.team_id, payload.name):
        return channel_name_conflict_response(payload.name)

    team = teams_repo.get_team(payload.team_id)

    try:
        channel = channels_repo.create_channel(
            team_id=payload.team_id,
            name=payload.name,
            channel_type=payload.channel_type,
            config=payload.config,
            enabled=payload.enabled,
            group_id=team.group_id,
        )
    except IntegrityError as exc:
        if is_channel_name_unique_violation(exc):
            return channel_name_conflict_response(payload.name)
        raise

    write_audit(
        "channel.create",
        object_type="channel",
        object_id=channel.id,
        team_id=channel.team.id if channel.team else None,
        data=payload.model_dump(),
    )

    return jsonify(serialize_channel(channel)), 201


@channels_bp.route("/<int:channel_id>", methods=["PUT"])
def update_channel(channel_id):
    """Update a notification channel."""
    payload, error = validate_body(ChannelUpdateSchema)
    if error:
        return error

    current_channel = channels_repo.get_channel(channel_id)

    if current_channel.team_id:
        error = require_team_write(current_channel.team_id)
        if error:
            return error

    if payload.team_id and payload.team_id != current_channel.team_id:
        error = require_team_write(payload.team_id)
        if error:
            return error

    target_team_id = payload.team_id or current_channel.team_id

    if has_channel_name_conflict(
        target_team_id,
        payload.name,
        exclude_channel_id=current_channel.id,
    ):
        return channel_name_conflict_response(payload.name)

    update_data = {
        "team": payload.team_id,
        "name": payload.name,
        "channel_type": payload.channel_type,
        "config": payload.config,
        "enabled": payload.enabled,
    }

    if payload.team_id and payload.team_id != current_channel.team_id:
        update_data["group"] = teams_repo.get_team(payload.team_id).group_id

    try:
        channel = channels_repo.update_channel(channel_id, update_data)
    except IntegrityError as exc:
        if is_channel_name_unique_violation(exc):
            return channel_name_conflict_response(payload.name)
        raise

    write_audit(
        "channel.update",
        object_type="channel",
        object_id=channel.id,
        team_id=channel.team.id if channel.team else None,
        data=payload.model_dump(),
    )

    return jsonify(serialize_channel(channel))


@channels_bp.route("/<int:channel_id>/disable", methods=["POST"])
def disable_channel(channel_id):
    """Disable a notification channel without deleting it."""
    channel_before = channels_repo.get_channel(channel_id)

    if channel_before.team_id:
        error = require_team_write(channel_before.team_id)
        if error:
            return error

    channel = channels_repo.disable_channel(channel_id)

    write_audit(
        "channel.disable",
        object_type="channel",
        object_id=channel.id,
        team_id=channel.team.id if channel.team else None,
        data={"name": channel.name, "enabled": False},
    )

    return jsonify(serialize_channel(channel))


@channels_bp.route("/<int:channel_id>/enable", methods=["POST"])
def enable_channel(channel_id):
    """Enable a disabled notification channel."""
    channel_before = channels_repo.get_channel(channel_id)

    if channel_before.team_id:
        error = require_team_write(channel_before.team_id)
        if error:
            return error

    channel = channels_repo.enable_channel(channel_id)

    write_audit(
        "channel.enable",
        object_type="channel",
        object_id=channel.id,
        team_id=channel.team.id if channel.team else None,
        data={"name": channel.name, "enabled": True},
    )

    return jsonify(serialize_channel(channel))


@channels_bp.route("/<int:channel_id>", methods=["DELETE"])
def delete_channel(channel_id):
    """Delete a notification channel.

    The channel is soft-deleted so historical data remains preserved.
    """
    channel_before = channels_repo.get_channel(channel_id)

    if channel_before.team_id:
        error = require_team_write(channel_before.team_id)
        if error:
            return error

    channel = channels_repo.delete_channel(channel_id)

    write_audit(
        "channel.delete",
        object_type="channel",
        object_id=channel.id,
        team_id=channel.team.id if channel.team else None,
        data={
            "name": channel.name,
            "channel_type": channel.channel_type,
            "deleted": True,
        },
    )

    return jsonify({"deleted": True, "id": channel.id, "name": channel.name})


@channels_bp.route("/<int:channel_id>/test", methods=["POST"])
def test_channel(channel_id):
    """Send a test notification through a channel."""
    channel = channels_repo.get_channel(channel_id)

    if channel.team_id:
        error = require_team_read(channel.team_id)
        if error:
            return error

    notifier = get_notifier(channel.channel_type)
    team = channel.team
    fake_alert = SimpleNamespace(
        id=0,
        team=team,
        route=None,
        assignee=build_test_assignee(channel),
        status="test",
        source="manual-test",
        title="IncidentRelay test notification",
        message="This is a test notification from the IncidentRelay.",
        severity="info",
    )

    try:
        notifier.send(channel, fake_alert, "IncidentRelay test notification", event_type="test")
    except Exception as exc:
        write_audit(
            "channel.test.failed",
            object_type="channel",
            object_id=channel.id,
            team_id=team.id if team else None,
            message=str(exc),
        )
        return jsonify({"status": "failed", "error": str(exc)}), 400

    write_audit(
        "channel.test.sent",
        object_type="channel",
        object_id=channel.id,
        team_id=team.id if team else None,
    )

    return jsonify({"status": "sent"})


@channels_bp.route("/voice-providers", methods=["GET"])
def list_voice_call_providers():
    """Return available voice providers and their capabilities."""
    return jsonify(list_voice_providers())
