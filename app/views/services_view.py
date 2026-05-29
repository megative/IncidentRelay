from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from peewee import DoesNotExist, IntegrityError

from app.modules.db.models import Alert
from app.api.schemas.services import (
    ServiceCreateSchema,
    ServiceDependencyCreateSchema,
    ServiceDependencyUpdateSchema,
    ServiceLinkCreateSchema,
    ServiceLinkUpdateSchema,
    ServiceMatchRuleCreateSchema,
    ServiceMatchRuleUpdateSchema,
    ServiceRunbookCreateSchema,
    ServiceRunbookUpdateSchema,
    ServiceUpdateSchema,
)
from app.modules.db import (
    escalation_policies_repo,
    rotations_repo,
    routes_repo,
    services_repo,
)
from app.modules.db.common import integrity_conflict, unique_field_conflict
from app.services.audit import write_audit
from app.services.rbac import (
    current_user,
    get_allowed_team_ids,
    require_team_read,
    require_team_write,
)
from app.services.serializers import (
    serialize_service,
    serialize_service_dependency,
    serialize_service_link,
    serialize_service_match_rule,
    serialize_service_runbook,
    serialize_utc_datetime,
)
from app.services.validation import validate_body

services_bp = Blueprint("services_api", __name__)


def _json_error(error, message, status=400, **extra):
    payload = {"error": error, "message": message}
    payload.update(extra)
    return jsonify(payload), status


def _readable_services_from_request():
    """Return services visible to current user for aggregate service context endpoints."""
    team_id = request.args.get("team_id", type=int)
    service_id = request.args.get("service_id", type=int)

    if service_id:
        try:
            service = services_repo.get_service(service_id)
        except DoesNotExist:
            return None, _json_error(
                "service_not_found",
                "Service was not found",
                404,
                service_id=service_id,
            )

        error = require_team_read(service.team_id)
        if error:
            return None, error

        return [service], None

    services = services_repo.list_services(team_id=team_id)
    visible = []

    for service in services:
        error = require_team_read(service.team_id)
        if not error:
            visible.append(service)

    return visible, None


def _validate_dependency_service(service, depends_on_service_id):
    """Validate dependency target.

    Cross-team dependencies are allowed.
    User must be able to edit source service and read target service.
    """
    if service.id == depends_on_service_id:
        return _json_error(
            "dependency_self_reference",
            "Service cannot depend on itself",
            400,
            service_id=service.id,
        )

    try:
        depends_on = services_repo.get_service(depends_on_service_id)
    except DoesNotExist:
        return _json_error(
            "dependency_service_not_found",
            "Dependency service was not found",
            400,
            depends_on_service_id=depends_on_service_id,
        )

    if not depends_on.enabled:
        return _json_error(
            "dependency_service_disabled",
            "Dependency service is disabled",
            400,
            depends_on_service_id=depends_on.id,
        )

    error = require_team_read(depends_on.team_id)
    if error:
        return error

    return None


def _validate_rotation(team_id, rotation_id):
    if not rotation_id:
        return None

    try:
        rotation = rotations_repo.get_rotation(rotation_id)
    except DoesNotExist:
        return _json_error(
            "rotation_not_found",
            "Default rotation was not found",
            400,
            rotation_id=rotation_id,
        )

    if rotation.team_id != team_id:
        return _json_error(
            "rotation_team_mismatch",
            "Default rotation does not belong to service team",
            400,
            rotation_id=rotation_id,
            rotation_team_id=rotation.team_id,
            team_id=team_id,
        )

    return None


def _validate_escalation_policy(team_id, policy_id):
    if not policy_id:
        return None

    try:
        policy = escalation_policies_repo.get_policy(policy_id)
    except DoesNotExist:
        return _json_error(
            "escalation_policy_not_found",
            "Default escalation policy was not found",
            400,
            escalation_policy_id=policy_id,
        )

    if policy.team_id != team_id:
        return _json_error(
            "escalation_policy_team_mismatch",
            "Default escalation policy does not belong to service team",
            400,
            escalation_policy_id=policy_id,
            policy_team_id=policy.team_id,
            team_id=team_id,
        )

    return None


def _validate_route(team_id, route_id):
    if not route_id:
        return None

    try:
        route = routes_repo.get_route(route_id)
    except DoesNotExist:
        return _json_error(
            "route_not_found",
            "Route was not found",
            400,
            route_id=route_id,
        )

    if route.team_id != team_id:
        return _json_error(
            "route_team_mismatch",
            "Route does not belong to service match rule team",
            400,
            route_id=route_id,
            route_team_id=route.team_id,
            team_id=team_id,
        )

    return None


def _validate_service(team_id, service_id):
    try:
        service = services_repo.get_service(service_id)
    except DoesNotExist:
        return _json_error(
            "service_not_found",
            "Service was not found",
            400,
            service_id=service_id,
        )

    if service.team_id != team_id:
        return _json_error(
            "service_team_mismatch",
            "Service does not belong to match rule team",
            400,
            service_id=service_id,
            service_team_id=service.team_id,
            team_id=team_id,
        )

    if not service.enabled:
        return _json_error(
            "service_disabled",
            "Service is disabled",
            400,
            service_id=service_id,
        )

    return None


def _validate_service_payload(payload):
    rotation_error = _validate_rotation(payload.team_id, payload.default_rotation_id)
    if rotation_error:
        return rotation_error

    policy_error = _validate_escalation_policy(
        payload.team_id,
        payload.default_escalation_policy_id,
    )
    if policy_error:
        return policy_error

    return None


def _service_data_from_payload(payload):
    return {
        "team": payload.team_id,
        "slug": payload.slug,
        "name": payload.name,
        "description": payload.description,
        "service_type": payload.service_type,
        "environment": payload.environment,
        "criticality": payload.criticality,
        "tier": payload.tier,
        "status": payload.status,
        "status_source": payload.status_source,
        "status_message": payload.status_message,
        "default_rotation": payload.default_rotation_id,
        "default_escalation_policy": payload.default_escalation_policy_id,
        "labels": payload.labels,
        "tags": payload.tags,
        "metadata": payload.metadata,
        "enabled": payload.enabled,
        "public": payload.public,
        "public_name": payload.public_name,
        "public_description": payload.public_description,
        "public_order": payload.public_order,
    }


def _validate_match_rule_payload(payload):
    service_error = _validate_service(payload.team_id, payload.service_id)
    if service_error:
        return service_error

    route_error = _validate_route(payload.team_id, payload.route_id)
    if route_error:
        return route_error

    return None


def _match_rule_data_from_payload(payload):
    return {
        "team": payload.team_id,
        "route": payload.route_id,
        "service": payload.service_id,
        "position": payload.position,
        "name": payload.name,
        "description": payload.description,
        "matchers": payload.matchers,
        "enabled": payload.enabled,
    }


@services_bp.route("", methods=["GET"])
def list_services():
    """Return services visible to current user."""
    team_id = request.args.get("team_id", type=int)

    if team_id:
        error = require_team_read(team_id)
        if error:
            return error

        services = services_repo.list_services(team_id=team_id)
    else:
        services = services_repo.list_services(team_ids=get_allowed_team_ids())

    return jsonify([
        serialize_service(service, current_user())
        for service in services
    ])


@services_bp.route("/<int:service_id>", methods=["GET"])
def get_service(service_id):
    """Return one service."""
    service = services_repo.get_service(service_id)

    error = require_team_read(service.team_id)
    if error:
        return error

    return jsonify(serialize_service(service, current_user()))


@services_bp.route("", methods=["POST"])
def create_service():
    """Create a service."""
    payload, error = validate_body(ServiceCreateSchema)
    if error:
        return error

    error = require_team_write(payload.team_id)
    if error:
        return error

    validation_error = _validate_service_payload(payload)
    if validation_error:
        return validation_error

    try:
        service = services_repo.create_service(_service_data_from_payload(payload))
    except IntegrityError as exc:
        error_text = str(exc).lower()
        if "slug" in error_text:
            return unique_field_conflict(
                "slug",
                payload.slug,
                "Service with this slug already exists in this team",
            )
        return integrity_conflict(
            "Service could not be saved because it conflicts with existing data"
        )

    write_audit(
        "service.create",
        object_type="service",
        object_id=service.id,
        group_id=service.group_id,
        team_id=service.team_id,
        data=payload.model_dump(),
    )

    return jsonify(serialize_service(service, current_user())), 201


@services_bp.route("/<int:service_id>", methods=["PUT"])
def update_service(service_id):
    """Update a service."""
    service_before = services_repo.get_service(service_id)

    error = require_team_write(service_before.team_id)
    if error:
        return error

    payload, error = validate_body(ServiceUpdateSchema)
    if error:
        return error

    error = require_team_write(payload.team_id)
    if error:
        return error

    validation_error = _validate_service_payload(payload)
    if validation_error:
        return validation_error

    try:
        service = services_repo.update_service(
            service_id,
            _service_data_from_payload(payload),
        )
    except IntegrityError as exc:
        error_text = str(exc).lower()
        if "slug" in error_text:
            return unique_field_conflict(
                "slug",
                payload.slug,
                "Service with this slug already exists in this team",
            )
        return integrity_conflict(
            "Service could not be saved because it conflicts with existing data"
        )

    write_audit(
        "service.update",
        object_type="service",
        object_id=service.id,
        group_id=service.group_id,
        team_id=service.team_id,
        data=payload.model_dump(),
    )

    return jsonify(serialize_service(service, current_user()))


@services_bp.route("/<int:service_id>", methods=["DELETE"])
def delete_service(service_id):
    """Soft-delete a service."""
    service_before = services_repo.get_service(service_id)

    error = require_team_write(service_before.team_id)
    if error:
        return error

    service = services_repo.soft_delete_service(service_id)

    write_audit(
        "service.delete",
        object_type="service",
        object_id=service.id,
        group_id=service.group_id,
        team_id=service.team_id,
        data={"deleted": True},
    )

    return jsonify({"deleted": True, "id": service.id})


@services_bp.route("/match-rules", methods=["GET"])
def list_match_rules():
    """Return service match rules filtered by team, route or service."""
    team_id = request.args.get("team_id", type=int)
    route_id = request.args.get("route_id", type=int)
    service_id = request.args.get("service_id", type=int)

    if route_id:
        try:
            route = routes_repo.get_route(route_id)
        except DoesNotExist:
            return _json_error(
                "route_not_found",
                "Route was not found",
                404,
                route_id=route_id,
            )

        error = require_team_read(route.team_id)
        if error:
            return error

        team_id = route.team_id

    elif service_id:
        service = services_repo.get_service(service_id)

        error = require_team_read(service.team_id)
        if error:
            return error

        team_id = service.team_id

    elif team_id:
        error = require_team_read(team_id)
        if error:
            return error

    else:
        return _json_error(
            "team_required",
            "team_id, route_id or service_id is required",
            400,
        )

    rules = services_repo.list_match_rules(
        service_id=service_id,
        team_id=team_id,
        route_id=route_id,
    )

    return jsonify([
        serialize_service_match_rule(rule, current_user())
        for rule in rules
    ])


@services_bp.route("/<int:service_id>/match-rules", methods=["GET"])
def list_service_match_rules(service_id):
    """Return match rules for a service."""
    service = services_repo.get_service(service_id)

    error = require_team_read(service.team_id)
    if error:
        return error

    return jsonify([
        serialize_service_match_rule(rule, current_user())
        for rule in services_repo.list_match_rules(service_id=service_id)
    ])


@services_bp.route("/<int:service_id>/match-rules", methods=["POST"])
def create_service_match_rule(service_id):
    """Create a service match rule."""
    payload, error = validate_body(ServiceMatchRuleCreateSchema)
    if error:
        return error

    if payload.service_id != service_id:
        return _json_error(
            "service_id_mismatch",
            "service_id in URL and body must match",
            400,
            url_service_id=service_id,
            payload_service_id=payload.service_id,
        )

    error = require_team_write(payload.team_id)
    if error:
        return error

    validation_error = _validate_match_rule_payload(payload)
    if validation_error:
        return validation_error

    rule = services_repo.create_match_rule(_match_rule_data_from_payload(payload))

    write_audit(
        "service_match_rule.create",
        object_type="service_match_rule",
        object_id=rule.id,
        team_id=rule.team_id,
        data=payload.model_dump(),
    )

    return jsonify(serialize_service_match_rule(rule, current_user())), 201


@services_bp.route("/match-rules/<int:rule_id>", methods=["PUT"])
def update_service_match_rule(rule_id):
    """Update a service match rule."""
    rule_before = services_repo.get_match_rule(rule_id)

    error = require_team_write(rule_before.team_id)
    if error:
        return error

    payload, error = validate_body(ServiceMatchRuleUpdateSchema)
    if error:
        return error

    error = require_team_write(payload.team_id)
    if error:
        return error

    validation_error = _validate_match_rule_payload(payload)
    if validation_error:
        return validation_error

    rule = services_repo.update_match_rule(
        rule_id,
        _match_rule_data_from_payload(payload),
    )

    write_audit(
        "service_match_rule.update",
        object_type="service_match_rule",
        object_id=rule.id,
        team_id=rule.team_id,
        data=payload.model_dump(),
    )

    return jsonify(serialize_service_match_rule(rule, current_user()))


@services_bp.route("/match-rules/<int:rule_id>", methods=["DELETE"])
def delete_service_match_rule(rule_id):
    """Soft-delete a service match rule."""
    rule_before = services_repo.get_match_rule(rule_id)

    error = require_team_write(rule_before.team_id)
    if error:
        return error

    rule = services_repo.soft_delete_match_rule(rule_id)

    write_audit(
        "service_match_rule.delete",
        object_type="service_match_rule",
        object_id=rule.id,
        team_id=rule.team_id,
        data={"deleted": True},
    )

    return jsonify({"deleted": True, "id": rule.id})


@services_bp.route("/<int:service_id>/links", methods=["GET"])
def list_service_links(service_id):
    """Return service links."""
    service = services_repo.get_service(service_id)

    error = require_team_read(service.team_id)
    if error:
        return error

    return jsonify([
        serialize_service_link(link, current_user())
        for link in services_repo.list_service_links(service_id)
    ])


@services_bp.route("/<int:service_id>/links", methods=["POST"])
def create_service_link(service_id):
    """Create a service link."""
    service = services_repo.get_service(service_id)

    error = require_team_write(service.team_id)
    if error:
        return error

    payload, error = validate_body(ServiceLinkCreateSchema)
    if error:
        return error

    link = services_repo.create_service_link(
        service_id,
        payload.model_dump(),
    )

    write_audit(
        "service_link.create",
        object_type="service_link",
        object_id=link.id,
        group_id=service.group_id,
        team_id=service.team_id,
        data=payload.model_dump(),
    )

    return jsonify(serialize_service_link(link, current_user())), 201


@services_bp.route("/links/<int:link_id>", methods=["PUT"])
def update_service_link(link_id):
    """Update a service link."""
    link_before = services_repo.get_service_link(link_id)

    error = require_team_write(link_before.service.team_id)
    if error:
        return error

    payload, error = validate_body(ServiceLinkUpdateSchema)
    if error:
        return error

    link = services_repo.update_service_link(
        link_id,
        payload.model_dump(),
    )

    write_audit(
        "service_link.update",
        object_type="service_link",
        object_id=link.id,
        group_id=link.service.group_id,
        team_id=link.service.team_id,
        data=payload.model_dump(),
    )

    return jsonify(serialize_service_link(link, current_user()))


@services_bp.route("/links/<int:link_id>", methods=["DELETE"])
def delete_service_link(link_id):
    """Delete a service link."""
    link_before = services_repo.get_service_link(link_id)

    error = require_team_write(link_before.service.team_id)
    if error:
        return error

    link = services_repo.soft_delete_service_link(link_id)

    write_audit(
        "service_link.delete",
        object_type="service_link",
        object_id=link.id,
        group_id=link.service.group_id,
        team_id=link.service.team_id,
        data={"deleted": True},
    )

    return jsonify({"deleted": True, "id": link.id})


@services_bp.route("/<int:service_id>/runbooks", methods=["GET"])
def list_service_runbooks(service_id):
    """Return service runbooks."""
    service = services_repo.get_service(service_id)

    error = require_team_read(service.team_id)
    if error:
        return error

    return jsonify([
        serialize_service_runbook(runbook, current_user())
        for runbook in services_repo.list_service_runbooks(service_id)
    ])


@services_bp.route("/<int:service_id>/runbooks", methods=["POST"])
def create_service_runbook(service_id):
    """Create a service runbook."""
    service = services_repo.get_service(service_id)

    error = require_team_write(service.team_id)
    if error:
        return error

    payload, error = validate_body(ServiceRunbookCreateSchema)
    if error:
        return error

    runbook = services_repo.create_service_runbook(
        service_id,
        payload.model_dump(),
    )

    write_audit(
        "service_runbook.create",
        object_type="service_runbook",
        object_id=runbook.id,
        group_id=service.group_id,
        team_id=service.team_id,
        data=payload.model_dump(),
    )

    return jsonify(serialize_service_runbook(runbook, current_user())), 201


@services_bp.route("/runbooks/<int:runbook_id>", methods=["PUT"])
def update_service_runbook(runbook_id):
    """Update a service runbook."""
    runbook_before = services_repo.get_service_runbook(runbook_id)

    error = require_team_write(runbook_before.service.team_id)
    if error:
        return error

    payload, error = validate_body(ServiceRunbookUpdateSchema)
    if error:
        return error

    runbook = services_repo.update_service_runbook(
        runbook_id,
        payload.model_dump(),
    )

    write_audit(
        "service_runbook.update",
        object_type="service_runbook",
        object_id=runbook.id,
        group_id=runbook.service.group_id,
        team_id=runbook.service.team_id,
        data=payload.model_dump(),
    )

    return jsonify(serialize_service_runbook(runbook, current_user()))


@services_bp.route("/runbooks/<int:runbook_id>", methods=["DELETE"])
def delete_service_runbook(runbook_id):
    """Delete a service runbook."""
    runbook_before = services_repo.get_service_runbook(runbook_id)

    error = require_team_write(runbook_before.service.team_id)
    if error:
        return error

    runbook = services_repo.soft_delete_service_runbook(runbook_id)

    write_audit(
        "service_runbook.delete",
        object_type="service_runbook",
        object_id=runbook.id,
        group_id=runbook.service.group_id,
        team_id=runbook.service.team_id,
        data={"deleted": True},
    )

    return jsonify({"deleted": True, "id": runbook.id})


@services_bp.route("/<int:service_id>/dependencies", methods=["GET"])
def list_service_dependencies(service_id):
    """Return service dependencies."""
    service = services_repo.get_service(service_id)

    error = require_team_read(service.team_id)
    if error:
        return error

    return jsonify([
        serialize_service_dependency(dependency, current_user())
        for dependency in services_repo.list_service_dependencies(service_id)
    ])


@services_bp.route("/<int:service_id>/dependencies", methods=["POST"])
def create_service_dependency(service_id):
    """Create a service dependency."""
    service = services_repo.get_service(service_id)

    error = require_team_write(service.team_id)
    if error:
        return error

    payload, error = validate_body(ServiceDependencyCreateSchema)
    if error:
        return error

    validation_error = _validate_dependency_service(
        service,
        payload.depends_on_service_id,
    )
    if validation_error:
        return validation_error

    dependency = services_repo.create_service_dependency(
        service_id,
        {
            "depends_on_service": payload.depends_on_service_id,
            "dependency_type": payload.dependency_type,
            "criticality": payload.criticality,
            "description": payload.description,
            "enabled": payload.enabled,
        },
    )

    write_audit(
        "service_dependency.create",
        object_type="service_dependency",
        object_id=dependency.id,
        group_id=service.group_id,
        team_id=service.team_id,
        data=payload.model_dump(),
    )

    return jsonify(serialize_service_dependency(dependency, current_user())), 201


@services_bp.route("/dependencies/<int:dependency_id>", methods=["PUT"])
def update_service_dependency(dependency_id):
    """Update a service dependency."""
    dependency_before = services_repo.get_service_dependency(dependency_id)
    service = dependency_before.service

    error = require_team_write(service.team_id)
    if error:
        return error

    payload, error = validate_body(ServiceDependencyUpdateSchema)
    if error:
        return error

    validation_error = _validate_dependency_service(
        service,
        payload.depends_on_service_id,
    )
    if validation_error:
        return validation_error

    dependency = services_repo.update_service_dependency(
        dependency_id,
        {
            "depends_on_service": payload.depends_on_service_id,
            "dependency_type": payload.dependency_type,
            "criticality": payload.criticality,
            "description": payload.description,
            "enabled": payload.enabled,
        },
    )

    write_audit(
        "service_dependency.update",
        object_type="service_dependency",
        object_id=dependency.id,
        group_id=service.group_id,
        team_id=service.team_id,
        data=payload.model_dump(),
    )

    return jsonify(serialize_service_dependency(dependency, current_user()))


@services_bp.route("/dependencies/<int:dependency_id>", methods=["DELETE"])
def delete_service_dependency(dependency_id):
    """Delete a service dependency."""
    dependency_before = services_repo.get_service_dependency(dependency_id)
    service = dependency_before.service

    error = require_team_write(service.team_id)
    if error:
        return error

    dependency = services_repo.soft_delete_service_dependency(dependency_id)

    write_audit(
        "service_dependency.delete",
        object_type="service_dependency",
        object_id=dependency.id,
        group_id=service.group_id,
        team_id=service.team_id,
        data={"deleted": True},
    )

    return jsonify({"deleted": True, "id": dependency.id})


@services_bp.route("/links", methods=["GET"])
def list_all_service_links():
    """Return links for all readable services in current scope."""
    services, error = _readable_services_from_request()
    if error:
        return error

    service_ids = [service.id for service in services]

    return jsonify([
        serialize_service_link(link, current_user())
        for link in services_repo.list_service_links(service_ids=service_ids)
    ])


@services_bp.route("/runbooks", methods=["GET"])
def list_all_service_runbooks():
    """Return runbooks for all readable services in current scope."""
    services, error = _readable_services_from_request()
    if error:
        return error

    service_ids = [service.id for service in services]

    return jsonify([
        serialize_service_runbook(runbook, current_user())
        for runbook in services_repo.list_service_runbooks(service_ids=service_ids)
    ])


@services_bp.route("/dependencies", methods=["GET"])
def list_all_service_dependencies():
    """Return dependencies for all readable services in current scope."""
    services, error = _readable_services_from_request()
    if error:
        return error

    service_ids = [service.id for service in services]

    return jsonify([
        serialize_service_dependency(dependency, current_user())
        for dependency in services_repo.list_service_dependencies(service_ids=service_ids)
    ])


@services_bp.route("/analytics", methods=["GET"])
def service_analytics():
    """Return alert analytics grouped by affected service."""
    services, error = _readable_services_from_request()
    if error:
        return error

    days = request.args.get("days", default=30, type=int)
    days = max(1, min(days or 30, 365))

    service_ids = [service.id for service in services]
    if not service_ids:
        return jsonify([])

    since = datetime.utcnow() - timedelta(days=days)

    stats = {}

    for service in services:
        stats[service.id] = {
            "service_id": service.id,
            "service_name": service.name,
            "service_slug": service.slug,
            "team_id": service.team_id,
            "team_name": service.team.name if service.team else None,
            "team_slug": service.team.slug if service.team else None,
            "service_status": service.status,
            "service_criticality": service.criticality,
            "service_environment": service.environment,
            "service_tier": service.tier,
            "total_alerts": 0,
            "open_alerts": 0,
            "firing_alerts": 0,
            "acknowledged_alerts": 0,
            "resolved_alerts": 0,
            "silenced_alerts": 0,
            "critical_open_alerts": 0,
            "warning_open_alerts": 0,
            "last_alert_at": None,
            "_last_alert_at_value": None,
        }

    alerts = (
        Alert
        .select()
        .where(
            (Alert.service.in_(service_ids))
            & (Alert.first_seen_at >= since)
        )
    )

    for alert in alerts:
        service_id = alert.service_id
        item = stats.get(service_id)
        if not item:
            continue

        status = (alert.status or "").lower()
        severity = (alert.severity or "unknown").lower()
        is_open = status in {"firing", "acknowledged"}

        item["total_alerts"] += 1

        if status == "firing":
            item["firing_alerts"] += 1

        if status == "acknowledged":
            item["acknowledged_alerts"] += 1

        if status == "resolved":
            item["resolved_alerts"] += 1

        if is_open:
            item["open_alerts"] += 1

        if alert.silenced:
            item["silenced_alerts"] += 1

        if is_open and severity in {"critical", "crit", "fatal"}:
            item["critical_open_alerts"] += 1

        if is_open and severity in {"warning", "warn"}:
            item["warning_open_alerts"] += 1

        last_alert_at = alert.last_seen_at or alert.first_seen_at
        if last_alert_at and (
            item["_last_alert_at_value"] is None
            or last_alert_at > item["_last_alert_at_value"]
        ):
            item["_last_alert_at_value"] = last_alert_at
            item["last_alert_at"] = serialize_utc_datetime(last_alert_at)

    result = []

    for item in stats.values():
        item.pop("_last_alert_at_value", None)
        result.append(item)

    result.sort(
        key=lambda row: (
            row["open_alerts"],
            row["critical_open_alerts"],
            row["total_alerts"],
        ),
        reverse=True,
    )

    return jsonify(result)


SERVICE_STATUS_RANK = {
    "disabled": -1,
    "operational": 0,
    "unknown": 1,
    "maintenance": 2,
    "degraded": 3,
    "partial_outage": 4,
    "major_outage": 5,
}


def _service_status_rank(status):
    """Return comparable service status rank."""
    return SERVICE_STATUS_RANK.get(status or "unknown", 1)


def _worst_service_status(statuses):
    """Return worst service status from a list."""
    statuses = [
        status
        for status in statuses
        if status
    ]

    if not statuses:
        return "operational"

    return max(
        statuses,
        key=lambda status: _service_status_rank(status),
    )


def _alert_impact_status(alert):
    """Return service impact status for one open alert."""
    if alert.silenced:
        return "operational"

    status = (alert.status or "").lower()
    if status not in {"firing", "acknowledged"}:
        return "operational"

    severity = (alert.severity or "unknown").lower()

    if severity in {"critical", "crit", "fatal"}:
        return "major_outage"

    if severity in {"warning", "warn"}:
        return "degraded"

    if severity in {"info", "informational", "none"}:
        return "operational"

    return "degraded"


def _build_alert_impact_by_service(service_ids, days=30):
    """Return alert impact grouped by service."""
    if not service_ids:
        return {}

    since = datetime.utcnow() - timedelta(days=days)

    rows = (
        Alert
        .select()
        .where(
            (Alert.service.in_(service_ids))
            & (Alert.first_seen_at >= since)
            & (Alert.status.in_(["firing", "acknowledged"]))
            & (Alert.silenced == False)
        )
    )

    result = {}

    for alert in rows:
        service_id = alert.service_id
        item = result.setdefault(
            service_id,
            {
                "alert_impact_status": "operational",
                "open_alerts": 0,
                "critical_open_alerts": 0,
                "warning_open_alerts": 0,
            },
        )

        impact_status = _alert_impact_status(alert)

        item["open_alerts"] += 1

        severity = (alert.severity or "unknown").lower()
        if severity in {"critical", "crit", "fatal"}:
            item["critical_open_alerts"] += 1

        if severity in {"warning", "warn"}:
            item["warning_open_alerts"] += 1

        item["alert_impact_status"] = _worst_service_status([
            item["alert_impact_status"],
            impact_status,
        ])

    return result


def _base_service_impact_row(service, alert_impact):
    """Build service impact row without dependency propagation."""
    own_status = service.status or "unknown"

    alert_data = alert_impact.get(
        service.id,
        {
            "alert_impact_status": "operational",
            "open_alerts": 0,
            "critical_open_alerts": 0,
            "warning_open_alerts": 0,
        },
    )

    alert_impact_status = alert_data["alert_impact_status"]

    effective_status = _worst_service_status([
        own_status,
        alert_impact_status,
    ])

    if not service.enabled:
        effective_status = "disabled"

    return {
        "service_id": service.id,
        "service_name": service.name,
        "service_slug": service.slug,
        "team_id": service.team_id,
        "team_name": service.team.name if service.team else None,
        "team_slug": service.team.slug if service.team else None,

        "own_status": own_status,
        "alert_impact_status": alert_impact_status,
        "dependency_impact_status": "operational",
        "effective_status": effective_status,

        "has_alert_impact": alert_impact_status != "operational",
        "has_dependency_impact": False,

        "open_alerts": alert_data["open_alerts"],
        "critical_open_alerts": alert_data["critical_open_alerts"],
        "warning_open_alerts": alert_data["warning_open_alerts"],

        "upstream_issues_count": 0,
        "upstream_issues": [],

        "criticality": service.criticality,
        "environment": service.environment,
        "tier": service.tier,
        "enabled": service.enabled,
    }


def _apply_dependency_impact(row, dependencies, rows_by_service):
    """Apply direct dependency impact to a service row."""
    upstream_issues = []

    for dependency in dependencies:
        if not dependency.enabled:
            continue

        target = dependency.depends_on_service

        if not target or not target.enabled:
            continue

        error = require_team_read(target.team_id)
        if error:
            continue

        target_row = rows_by_service.get(target.id)
        target_status = (
            target_row["effective_status"]
            if target_row
            else target.status or "unknown"
        )

        if target_status == "operational":
            continue

        upstream_issues.append({
            "dependency_id": dependency.id,
            "dependency_type": dependency.dependency_type,
            "criticality": dependency.criticality,
            "description": dependency.description,
            "service_id": target.id,
            "service_name": target.name,
            "service_slug": target.slug,
            "team_id": target.team_id,
            "team_name": target.team.name if target.team else None,
            "team_slug": target.team.slug if target.team else None,
            "status": target_status,
        })

    dependency_impact_status = _worst_service_status([
        issue["status"]
        for issue in upstream_issues
    ])

    row["dependency_impact_status"] = dependency_impact_status
    row["has_dependency_impact"] = bool(upstream_issues)
    row["upstream_issues_count"] = len(upstream_issues)
    row["upstream_issues"] = upstream_issues

    row["effective_status"] = _worst_service_status([
        row["own_status"],
        row["alert_impact_status"],
        dependency_impact_status,
    ])

    if not row["enabled"]:
        row["effective_status"] = "disabled"

    return row


@services_bp.route("/impact", methods=["GET"])
def list_service_impact():
    """Return computed service impact based on alerts and dependencies."""
    services, error = _readable_services_from_request()
    if error:
        return error

    requested_service_ids = [service.id for service in services]
    if not requested_service_ids:
        return jsonify([])

    days = request.args.get("days", default=30, type=int)
    days = max(1, min(days or 30, 365))

    dependencies = services_repo.list_service_dependencies(
        service_ids=requested_service_ids,
    )

    impact_services_by_id = {
        service.id: service
        for service in services
    }

    for dependency in dependencies:
        if not dependency.enabled:
            continue

        target = dependency.depends_on_service
        if not target or not target.enabled:
            continue

        # Dependency impact must include upstream alert impact even when
        # the request is filtered by a single downstream service.
        error = require_team_read(target.team_id)
        if error:
            continue

        impact_services_by_id[target.id] = target

    impact_service_ids = list(impact_services_by_id.keys())

    alert_impact = _build_alert_impact_by_service(
        impact_service_ids,
        days=days,
    )

    rows_by_service = {
        service.id: _base_service_impact_row(
            service,
            alert_impact,
        )
        for service in impact_services_by_id.values()
    }

    dependencies_by_service = {}
    for dependency in dependencies:
        dependencies_by_service.setdefault(
            dependency.service_id,
            [],
        ).append(dependency)

    for service in services:
        row = rows_by_service[service.id]
        _apply_dependency_impact(
            row,
            dependencies_by_service.get(service.id, []),
            rows_by_service,
        )

    result = [
        rows_by_service[service.id]
        for service in services
    ]

    result.sort(
        key=lambda row: (
            _service_status_rank(row["effective_status"]),
            row["upstream_issues_count"],
            row["critical_open_alerts"],
            row["open_alerts"],
        ),
        reverse=True,
    )

    return jsonify(result)
