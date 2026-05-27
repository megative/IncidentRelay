from flask import Blueprint, jsonify, request
from peewee import DoesNotExist

from app.api.schemas.routes import RouteChannelsReplaceSchema, RouteCreateSchema, RouteUpdateSchema
from app.modules.db import routes_repo, channels_repo, rotations_repo
from app.services.auth import create_raw_token, hash_token
from app.services.audit import write_audit
from app.services.rbac import get_allowed_team_ids, require_team_read, require_team_write
from app.services.serializers import serialize_route
from app.services.validation import validate_body


routes_bp = Blueprint("routes_api", __name__)




def validate_route_rotation(team_id, rotation_id):
    """Ensure selected rotation exists and belongs to the route team."""
    if not rotation_id:
        return None

    try:
        rotation = rotations_repo.get_rotation(rotation_id)
    except DoesNotExist:
        return jsonify({
            "error": "rotation_not_found",
            "message": "Rotation was not found",
            "rotation_id": rotation_id,
        }), 400

    if rotation.team_id != team_id:
        return jsonify({
            "error": "rotation_team_mismatch",
            "message": "Rotation does not belong to route team",
            "rotation_id": rotation_id,
            "rotation_team_id": rotation.team_id,
            "team_id": team_id,
        }), 400

    return None


def validate_route_escalation_policy(team_id, escalation_policy_id):
    """Ensure selected escalation policy exists and belongs to the route team."""
    if not escalation_policy_id:
        return None

    try:
        policy = escalation_policies_repo.get_policy(escalation_policy_id)
    except DoesNotExist:
        return jsonify({
            "error": "escalation_policy_not_found",
            "message": "Escalation policy was not found",
            "escalation_policy_id": escalation_policy_id,
        }), 400

    if policy.team_id != team_id:
        return jsonify({
            "error": "escalation_policy_team_mismatch",
            "message": "Escalation policy does not belong to route team",
            "escalation_policy_id": escalation_policy_id,
            "policy_team_id": policy.team_id,
            "team_id": team_id,
        }), 400

    return None


def validate_route_channels(team_id, channel_ids):
    """Ensure all route channels exist and belong to the same team as the route."""
    for channel_id in channel_ids:
        try:
            channel = channels_repo.get_channel(channel_id)
        except DoesNotExist:
            return jsonify({
                "error": "channel_not_found",
                "message": "Channel was not found",
                "channel_id": channel_id,
            }), 400

        if channel.team_id != team_id:
            return jsonify({
                "error": "channel_team_mismatch",
                "message": "Channel does not belong to route team",
                "channel_id": channel_id,
                "channel_team_id": channel.team_id,
                "team_id": team_id,
            }), 400

        error = require_team_write(channel.team_id)
        if error:
            return error

    return None


def validate_route_rotation(team_id, rotation_id):
    """Ensure selected rotation exists and belongs to the route team."""
    if not rotation_id:
        return None

    try:
        rotation = rotations_repo.get_rotation(rotation_id)
    except DoesNotExist:
        return jsonify({
            "error": "rotation_not_found",
            "message": "Rotation was not found",
            "rotation_id": rotation_id,
        }), 400

    if rotation.team_id != team_id:
        return jsonify({
            "error": "rotation_team_mismatch",
            "message": "Rotation does not belong to route team",
            "rotation_id": rotation_id,
            "rotation_team_id": rotation.team_id,
            "team_id": team_id,
        }), 400

    error = require_team_write(rotation.team_id)
    if error:
        return error

    return None


@routes_bp.route("", methods=["GET"])
def list_routes():
    """
    Return alert routes.
    """

    team_id = request.args.get("team_id", type=int)

    if team_id:
        error = require_team_read(team_id)
        if error:
            return error
        routes = routes_repo.list_routes(team_id=team_id)
    else:
        routes = routes_repo.list_routes(team_ids=get_allowed_team_ids())

    return jsonify([serialize_route(route) for route in routes])


@routes_bp.route("/<int:route_id>", methods=["GET"])
def get_route(route_id):
    """
    Return a single route.
    """

    route = routes_repo.get_route(route_id)
    error = require_team_read(route.team_id)

    if error:
        return error

    return jsonify(serialize_route(route))


@routes_bp.route("", methods=["POST"])
def create_route():
    """
    Create an alert route with rotation, channels and route intake token.
    """

    payload, error = validate_body(RouteCreateSchema)
    if error:
        return error

    error = require_team_write(payload.team_id)
    if error:
        return error

    channel_error = validate_route_channels(payload.team_id, payload.channel_ids)
    if channel_error:
        return channel_error

    rotation_error = validate_route_rotation(payload.team_id, payload.rotation_id)
    if rotation_error:
        return rotation_error

    policy_error = validate_route_escalation_policy(payload.team_id, payload.escalation_policy_id)
    if policy_error:
        return policy_error

    rotation_error = validate_route_rotation(payload.team_id, payload.rotation_id)
    if rotation_error:
        return rotation_error

    raw_token = create_raw_token()

    route = routes_repo.create_route(
        team_id=payload.team_id,
        name=payload.name,
        source=payload.source,
        rotation_id=payload.rotation_id,
        matchers=payload.matchers,
        group_by=payload.group_by,
        enabled=payload.enabled,
        intake_token_prefix=raw_token[:12],
        intake_token_hash=hash_token(raw_token),
    )

    for channel_id in payload.channel_ids:
        routes_repo.link_route_channel(route.id, channel_id)

    write_audit(
        "route.create",
        object_type="route",
        object_id=route.id,
        team_id=route.team.id,
        data={**payload.model_dump(), "intake_token": "***"},
    )

    response = serialize_route(route)
    response["intake_token"] = raw_token

    return jsonify(response), 201


@routes_bp.route("/<int:route_id>", methods=["PUT"])
def update_route(route_id):
    """
    Update an alert route and its channel links.
    """

    payload, error = validate_body(RouteUpdateSchema)
    if error:
        return error

    current_route = routes_repo.get_route(route_id)
    error = require_team_write(current_route.team_id)

    if error:
        return error

    if payload.team_id != current_route.team_id:
        error = require_team_write(payload.team_id)
        if error:
            return error

    channel_error = validate_route_channels(payload.team_id, payload.channel_ids)
    if channel_error:
        return channel_error

    rotation_error = validate_route_rotation(payload.team_id, payload.rotation_id)
    if rotation_error:
        return rotation_error

    route = routes_repo.update_route(
        route_id,
        {
            "team": payload.team_id,
            "name": payload.name,
            "source": payload.source,
            "rotation": payload.rotation_id,
            "escalation_policy": payload.escalation_policy_id,
            "matchers": payload.matchers,
            "group_by": payload.group_by,
            "enabled": payload.enabled,
        },
    )

    routes_repo.replace_route_channels(route.id, payload.channel_ids)
    route = routes_repo.get_route(route_id)

    write_audit(
        "route.update",
        object_type="route",
        object_id=route.id,
        team_id=route.team.id,
        data=payload.model_dump(),
    )

    return jsonify(serialize_route(route))


@routes_bp.route("/<int:route_id>/disable", methods=["POST"])
def disable_route(route_id):
    """
    Disable an alert route without deleting it.
    """
    route_before = routes_repo.get_route(route_id)

    error = require_team_write(route_before.team_id)
    if error:
        return error

    route = routes_repo.disable_route(route_id)

    write_audit(
        "route.disable",
        object_type="route",
        object_id=route.id,
        team_id=route.team.id,
        data={
            "name": route.name,
            "enabled": False,
        },
    )

    return jsonify(serialize_route(route))


@routes_bp.route("/<int:route_id>/enable", methods=["POST"])
def enable_route(route_id):
    """
    Enable a disabled alert route.
    """
    route_before = routes_repo.get_route(route_id)

    error = require_team_write(route_before.team_id)
    if error:
        return error

    route = routes_repo.enable_route(route_id)

    write_audit(
        "route.enable",
        object_type="route",
        object_id=route.id,
        team_id=route.team.id,
        data={
            "name": route.name,
            "enabled": True,
        },
    )

    return jsonify(serialize_route(route))


@routes_bp.route("/<int:route_id>", methods=["DELETE"])
def delete_route(route_id):
    """
    Delete an alert route.

    The route is soft-deleted so historical alerts keep their route reference.
    """
    route_before = routes_repo.get_route(route_id)

    error = require_team_write(route_before.team_id)
    if error:
        return error

    route = routes_repo.soft_delete_route(route_id)

    write_audit(
        "route.delete",
        object_type="route",
        object_id=route.id,
        team_id=route.team.id,
        data={
            "name": route.name,
            "source": route.source,
            "deleted": True,
        },
    )

    return jsonify({
        "deleted": True,
        "id": route.id,
        "name": route.name,
    })


@routes_bp.route("/<int:route_id>/intake-token", methods=["POST"])
def regenerate_route_intake_token(route_id):
    """
    Regenerate the alert intake token for a route.
    """

    route = routes_repo.get_route(route_id)
    error = require_team_write(route.team_id)

    if error:
        return error

    raw_token = create_raw_token()
    route = routes_repo.set_route_intake_token(route_id, raw_token[:12], hash_token(raw_token))

    write_audit(
        "route.intake_token.regenerate",
        object_type="route",
        object_id=route.id,
        team_id=route.team.id,
    )

    response = serialize_route(route)
    response["intake_token"] = raw_token

    return jsonify(response)


@routes_bp.route("/<int:route_id>/channels", methods=["PUT"])
def replace_route_channels(route_id):
    """
    Replace all channels linked to a route.
    """

    payload, error = validate_body(RouteChannelsReplaceSchema)
    if error:
        return error

    route_before = routes_repo.get_route(route_id)
    error = require_team_write(route_before.team_id)

    if error:
        return error

    channel_error = validate_route_channels(route_before.team_id, payload.channel_ids)
    if channel_error:
        return channel_error

    routes_repo.replace_route_channels(route_id, payload.channel_ids)
    route = routes_repo.get_route(route_id)

    write_audit(
        "route.channels.replace",
        object_type="route",
        object_id=route_id,
        team_id=route.team.id,
        data=payload.model_dump(),
    )

    return jsonify(serialize_route(route))


@routes_bp.route("/<int:route_id>/channels/<int:channel_id>", methods=["POST"])
def add_route_channel(route_id, channel_id):
    """
    Link a channel to a route.
    """

    route_before = routes_repo.get_route(route_id)
    error = require_team_write(route_before.team_id)

    if error:
        return error

    channel_error = validate_route_channels(route_before.team_id, [channel_id])
    if channel_error:
        return channel_error

    link = routes_repo.link_route_channel(route_id, channel_id)

    write_audit(
        "route.channel.add",
        object_type="route",
        object_id=route_id,
        team_id=link.route.team.id,
        data={"channel_id": channel_id},
    )

    return jsonify({"id": link.id}), 201


@routes_bp.route("/<int:route_id>/channels/<int:channel_id>", methods=["DELETE"])
def delete_route_channel(route_id, channel_id):
    """
    Remove a channel from a route.
    """

    route_before = routes_repo.get_route(route_id)
    error = require_team_write(route_before.team_id)

    if error:
        return error

    routes_repo.unlink_route_channel(route_id, channel_id)
    return jsonify({"status": "deleted"})
