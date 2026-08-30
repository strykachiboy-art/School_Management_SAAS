from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from pydantic import ValidationError

from school_app.decorators import role_required
from school_app.enums.role import Role
from school_app.modules.audit.requests.audit_request import AuditLogFilterRequest
from school_app.modules.audit.services.audit_log_service import (
    get_filtered_audit_logs,
    get_audit_log,
)

audit_bp = Blueprint("audit", __name__, url_prefix="/audit-logs")

MAX_PER_PAGE = 100


def serialize_audit_log(log):
    return log.to_dict()


def _pagination_params():
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(request.args.get("per_page", 20, type=int), MAX_PER_PAGE)
    return page, per_page


def _paginated_response(result):
    return jsonify({
        "items": [serialize_audit_log(log) for log in result.items],
        "total": result.total,
        "page": result.page,
        "pages": result.pages,
    }), 200


def _format_validation_errors(exc: ValidationError):
    return [
        {"field": ".".join(str(p) for p in err["loc"]), "message": err["msg"]}
        for err in exc.errors()
    ]


@audit_bp.get("")
@jwt_required()
@role_required(Role.ADMIN)
def list_audit_logs():
    try:
        # Validate query parameters against your Pydantic filter schema
        filters = AuditLogFilterRequest.model_validate(request.args.to_dict())
    except ValidationError as exc:
        return jsonify({"details": _format_validation_errors(exc)}), 422

    result = get_filtered_audit_logs(
        actor_id=filters.actor_id,
        system_only=filters.system_only,
        action=filters.action,
        resource_type=filters.resource_type,
        resource_id=filters.resource_id,
        date_from=filters.date_from,
        date_to=filters.date_to,
        page=filters.page,
        per_page=filters.per_page,
    )
    return _paginated_response(result)


@audit_bp.get("/<int:log_id>")
@jwt_required()
@role_required(Role.ADMIN)
def get_single_audit_log(log_id):
    log = get_audit_log(log_id)
    if log is None:
        return jsonify({"error": "Audit log not found"}), 404
    return jsonify(serialize_audit_log(log)), 200