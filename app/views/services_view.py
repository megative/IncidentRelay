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


def _readable_services_from_request(*, include_disabled=True):
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

        if not include_disabled and not services_repo.is_service_active(service):
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

    services = services_repo.list_services(
        team_id=team_id,
        include_disabled=include_disabled,
    )

    visible = []
    for service in services:
        if not include_disabled and not services_repo.is_service_active(service):
            continue

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
    services, error = _readable_services_from_request(include_disabled=False)
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


def _downgrade_dependency_status(status, target_status):
    """Return the lower of status and target_status by service status rank."""
    if _service_status_rank(status) <= _service_status_rank(target_status):
        return status
    return target_status


def _dependency_downstream_impact_status(dependency, upstream_status):
    """
    Return downstream impact status caused by one upstream dependency.

    The upstream issue can still be shown in UI even when it does not change
    downstream effective_status.
    """
    upstream_status = upstream_status or "unknown"

    if upstream_status in {"operational", "disabled"}:
        return "operational"

    dependency_type = (dependency.dependency_type or "hard").lower()
    criticality = (dependency.criticality or "important").lower()

    if dependency_type == "informational":
        return "operational"

    if criticality == "optional":
        if upstream_status in {"major_outage", "partial_outage", "degraded"}:
            return "degraded"
        return "operational"

    if upstream_status == "maintenance":
        return "maintenance"

    if upstream_status == "unknown":
        return "unknown"

    if upstream_status == "major_outage":
        if criticality == "required" and dependency_type in {"hard", "external"}:
            return "major_outage"
        if criticality in {"required", "important"}:
            return "partial_outage"
        return "degraded"

    if upstream_status == "partial_outage":
        if criticality == "required" and dependency_type in {"hard", "external"}:
            return "partial_outage"
        return "degraded"

    if upstream_status == "degraded":
        return "degraded"

    return upstream_status


def _apply_dependency_impact(row, dependencies, rows_by_service, dependencies_by_service=None):
    """Apply dependency impact and attach full dependency paths."""
    dependencies_by_service = dependencies_by_service or {}

    service_id = row["service_id"]

    upstream_issues = _build_dependency_issue_paths(
        service_id=service_id,
        rows_by_service=rows_by_service,
        dependencies_by_service=dependencies_by_service,
        path_service_ids={service_id},
        depth=0,
        max_depth=SERVICE_IMPACT_MAX_DEPTH,
    )

    # Keep only issues from direct dependencies passed to this row.
    direct_dependency_ids = {
        dependency.id
        for dependency in dependencies
        if dependency.enabled
    }

    upstream_issues = [
        issue
        for issue in upstream_issues
        if issue.get("dependency_id") in direct_dependency_ids
    ]

    contributing_statuses = [
        issue["impact_status"]
        for issue in upstream_issues
        if issue.get("contributes_to_impact")
    ]

    dependency_impact_status = _worst_service_status(contributing_statuses)

    row["dependency_impact_status"] = dependency_impact_status
    row["has_dependency_impact"] = dependency_impact_status != "operational"
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


SERVICE_IMPACT_MAX_DEPTH = 3


def _collect_dependency_impact_context(services, max_depth=SERVICE_IMPACT_MAX_DEPTH):
    """
    Collect requested services plus readable upstream dependency services.

    This allows:
        frontend -> billing-api -> postgresql

    If postgresql has a critical alert, frontend can still receive dependency impact.
    """
    services_by_id = {
        service.id: service
        for service in services
    }

    dependencies_by_service = {}
    visited_service_ids = set(services_by_id.keys())
    frontier = set(services_by_id.keys())

    for _depth in range(max_depth):
        if not frontier:
            break

        dependencies = services_repo.list_service_dependencies(
            service_ids=list(frontier),
        )

        next_frontier = set()

        for dependency in dependencies:
            dependencies_by_service.setdefault(
                dependency.service_id,
                [],
            ).append(dependency)

            if not dependency.enabled:
                continue

            target = dependency.depends_on_service
            if not target or not target.enabled:
                continue

            error = require_team_read(target.team_id)
            if error:
                continue

            services_by_id[target.id] = target

            if target.id not in visited_service_ids:
                visited_service_ids.add(target.id)
                next_frontier.add(target.id)

        frontier = next_frontier

    return services_by_id, dependencies_by_service


def _service_display_name(service):
    """Return service display name using name first, then slug."""
    if not service:
        return "-"

    return service.name or service.slug or f"Service #{service.id}"


def _team_display_name(team):
    """Return team display name using name first, then slug."""
    if not team:
        return "-"

    return team.name or team.slug or f"Team #{team.id}"


def _service_path_node(service, row=None, dependency=None, *, cycle=False):
    """Build a dependency path node."""
    team = service.team if service else None

    return {
        "service_id": service.id if service else None,
        "service_name": service.name if service else None,
        "service_slug": service.slug if service else None,
        "service_display": _service_display_name(service),

        "team_id": team.id if team else None,
        "team_name": team.name if team else None,
        "team_slug": team.slug if team else None,
        "team_display": _team_display_name(team),

        "status": (
            row.get("effective_status")
            if row
            else service.status if service else "unknown"
        ),

        "dependency_id": dependency.id if dependency else None,
        "dependency_type": dependency.dependency_type if dependency else None,
        "criticality": dependency.criticality if dependency else None,
        "cycle": cycle,
    }


def _service_has_own_or_alert_impact(row):
    """Return true when service itself is a root cause candidate."""
    if not row:
        return False

    return (
        row.get("own_status") not in {None, "operational", "disabled"}
        or row.get("has_alert_impact") is True
    )


def _make_dependency_issue(
    *,
    direct_dependency,
    direct_service,
    direct_row,
    path,
    impact_status,
    contributes_to_impact,
    cycle_detected=False,
    depth_limited=False,
):
    """Build one upstream issue with full dependency path."""
    root = path[-1] if path else None

    return {
        "dependency_id": direct_dependency.id,
        "dependency_type": direct_dependency.dependency_type,
        "criticality": direct_dependency.criticality,
        "description": direct_dependency.description,

        # Direct upstream service. Kept for backward compatibility with UI.
        "service_id": direct_service.id,
        "service_name": direct_service.name,
        "service_slug": direct_service.slug,
        "service_display": _service_display_name(direct_service),

        "team_id": direct_service.team_id,
        "team_name": direct_service.team.name if direct_service.team else None,
        "team_slug": direct_service.team.slug if direct_service.team else None,
        "team_display": _team_display_name(direct_service.team),

        # Effective status of direct upstream.
        "status": direct_row.get("effective_status") if direct_row else direct_service.status,

        # What this dependency contributes to downstream.
        "impact_status": impact_status,
        "contributes_to_impact": contributes_to_impact,

        # Full path metadata.
        "path": path,
        "depth": max(len(path) - 1, 0),
        "cycle_detected": cycle_detected,
        "depth_limited": depth_limited,

        # Root cause metadata.
        "root_cause_service_id": root.get("service_id") if root else direct_service.id,
        "root_cause_service_name": root.get("service_name") if root else direct_service.name,
        "root_cause_service_slug": root.get("service_slug") if root else direct_service.slug,
        "root_cause_service_display": (
            root.get("service_display")
            if root
            else _service_display_name(direct_service)
        ),
        "root_cause_status": root.get("status") if root else (
            direct_row.get("effective_status") if direct_row else direct_service.status
        ),
    }


def _build_dependency_issue_paths(
    *,
    service_id,
    rows_by_service,
    dependencies_by_service,
    path_service_ids=None,
    depth=0,
    max_depth=SERVICE_IMPACT_MAX_DEPTH,
):
    """
    Return dependency issue paths for service_id.

    Each result describes one root-cause path visible from this service:

        Frontend -> Billing API -> PostgreSQL

    The returned path excludes the current service and starts with its direct
    upstream dependency.
    """
    path_service_ids = set(path_service_ids or [])
    issues = []

    if depth >= max_depth:
        return issues

    dependencies = dependencies_by_service.get(service_id, [])

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
            target_row.get("effective_status")
            if target_row
            else target.status or "unknown"
        )

        impact_status = _dependency_downstream_impact_status(
            dependency,
            target_status,
        )
        contributes_to_impact = impact_status != "operational"

        target_node = _service_path_node(
            target,
            target_row,
            dependency,
        )

        if target.id in path_service_ids:
            cycle_node = _service_path_node(
                target,
                target_row,
                dependency,
                cycle=True,
            )
            issues.append(
                _make_dependency_issue(
                    direct_dependency=dependency,
                    direct_service=target,
                    direct_row=target_row,
                    path=[cycle_node],
                    impact_status="operational",
                    contributes_to_impact=False,
                    cycle_detected=True,
                )
            )
            continue

        next_path_service_ids = set(path_service_ids)
        next_path_service_ids.add(target.id)

        child_issues = _build_dependency_issue_paths(
            service_id=target.id,
            rows_by_service=rows_by_service,
            dependencies_by_service=dependencies_by_service,
            path_service_ids=next_path_service_ids,
            depth=depth + 1,
            max_depth=max_depth,
        )

        # If the target has its own/manual/alert impact, it is a root cause.
        if target_status != "operational" and _service_has_own_or_alert_impact(target_row):
            issues.append(
                _make_dependency_issue(
                    direct_dependency=dependency,
                    direct_service=target,
                    direct_row=target_row,
                    path=[target_node],
                    impact_status=impact_status,
                    contributes_to_impact=contributes_to_impact,
                )
            )

        # If target is impacted by deeper dependencies, prepend target to each path.
        for child_issue in child_issues:
            child_path = child_issue.get("path") or []
            full_path = [target_node] + child_path

            issues.append(
                _make_dependency_issue(
                    direct_dependency=dependency,
                    direct_service=target,
                    direct_row=target_row,
                    path=full_path,
                    impact_status=impact_status,
                    contributes_to_impact=contributes_to_impact,
                    cycle_detected=bool(child_issue.get("cycle_detected")),
                    depth_limited=bool(child_issue.get("depth_limited")),
                )
            )

        # If target is non-operational but has no own/alert root and no child path,
        # keep it visible as a terminal upstream issue.
        if (
            target_status != "operational"
            and not _service_has_own_or_alert_impact(target_row)
            and not child_issues
        ):
            depth_limited = (
                depth + 1 >= max_depth
                and bool(dependencies_by_service.get(target.id))
            )

            issues.append(
                _make_dependency_issue(
                    direct_dependency=dependency,
                    direct_service=target,
                    direct_row=target_row,
                    path=[target_node],
                    impact_status=impact_status,
                    contributes_to_impact=contributes_to_impact,
                    depth_limited=depth_limited,
                )
            )

    return issues


def _compute_service_impact_row(
    service_id,
    rows_by_service,
    dependencies_by_service,
    state,
):
    """
    Compute effective status for one service after upstream rows are computed.

    Cycles are ignored safely:
        A -> B -> A

    In a cycle, the currently visiting row is returned as-is instead of recursing
    forever. The cycle itself is still visible through dependency issue paths.
    """
    current_state = state.get(service_id)

    if current_state == "done":
        return rows_by_service.get(service_id)

    if current_state == "visiting":
        return rows_by_service.get(service_id)

    row = rows_by_service.get(service_id)
    if not row:
        return None

    state[service_id] = "visiting"

    for dependency in dependencies_by_service.get(service_id, []):
        if not dependency.enabled:
            continue

        target = dependency.depends_on_service
        if not target:
            continue

        if target.id not in rows_by_service:
            continue

        _compute_service_impact_row(
            target.id,
            rows_by_service,
            dependencies_by_service,
            state,
        )

    _apply_dependency_impact(
        row,
        dependencies_by_service.get(service_id, []),
        rows_by_service,
        dependencies_by_service=dependencies_by_service,
    )

    state[service_id] = "done"
    return row


@services_bp.route("/impact", methods=["GET"])
def list_service_impact():
    """Return computed service impact based on alerts and dependencies."""
    services, error = _readable_services_from_request(include_disabled=False)
    if error:
        return error

    requested_service_ids = [service.id for service in services]
    if not requested_service_ids:
        return jsonify([])

    days = request.args.get("days", default=30, type=int)
    days = max(1, min(days or 30, 365))

    services_by_id, dependencies_by_service = _collect_dependency_impact_context(
        services,
        max_depth=SERVICE_IMPACT_MAX_DEPTH,
    )

    alert_impact = _build_alert_impact_by_service(
        list(services_by_id.keys()),
        days=days,
    )

    rows_by_service = {
        service.id: _base_service_impact_row(
            service,
            alert_impact,
        )
        for service in services_by_id.values()
    }

    state = {}

    for service_id in requested_service_ids:
        _compute_service_impact_row(
            service_id,
            rows_by_service,
            dependencies_by_service,
            state,
        )

    result = [
        rows_by_service[service_id]
        for service_id in requested_service_ids
        if service_id in rows_by_service
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
