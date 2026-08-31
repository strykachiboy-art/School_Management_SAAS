# school_app/modules/academics/routes/academic_session_routes.py

from flask import Blueprint, jsonify, request, abort, g
from school_app.decorators import role_required
from school_app.utils.helpers import validate_request
from school_app.enums.role import Role

from school_app.modules.academics.requests.academic_session_request import (
    AcademicSessionCreateRequest,
    AcademicSessionUpdateRequest,
    AcademicSessionResponse,
)

from school_app.modules.academics.services.academic_session_service import (
    create_academic_session,
    get_all_academic_session,
    get_academic_session,
    update_academic_session,
    delete_session,
    activate_academic_session,
)

academic_session_bp = Blueprint("academic_session", __name__, url_prefix="/academic-sessions")


# Create academic session
@academic_session_bp.route("/create", methods=["POST"])
@role_required(Role.ADMIN)
@validate_request(AcademicSessionCreateRequest)
def create_session(data: AcademicSessionCreateRequest):
    """
    Create a new academic session.
    The service will derive school_id from the actor if not provided in `data`.
    """
    session = create_academic_session(data, actor_id=g.user.id)
    serialized = AcademicSessionResponse.model_validate(session).model_dump(mode="json")
    return jsonify(serialized), 201


# List academic sessions
@academic_session_bp.route("", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER)
def get_all_sessions():
    search = request.args.get("search", "", type=str)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    result = get_all_academic_session(search=search, page=page, per_page=per_page)

    return jsonify({
        "items": [AcademicSessionResponse.model_validate(item).model_dump(mode="json") for item in result.items],
        "page": result.page,
        "pages": result.pages,
        "total": result.total,
    }), 200


# Get single academic session
@academic_session_bp.route("/<int:session_id>", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER)
def get_session(session_id):
    session = get_academic_session(session_id)
    if session is None:
        abort(404, description="Academic session not found")

    serialized = AcademicSessionResponse.model_validate(session).model_dump(mode="json")
    return jsonify(serialized), 200


# Update academic session (partial or full)
@academic_session_bp.route("/<int:session_id>/edit", methods=["PATCH", "PUT"])
@role_required(Role.ADMIN)
@validate_request(AcademicSessionUpdateRequest)
def update_session(data: AcademicSessionUpdateRequest, session_id):
    session = update_academic_session(data, session_id, actor_id=g.user.id)
    if session is None:
        abort(404, description="Academic session not found")

    serialized = AcademicSessionResponse.model_validate(session).model_dump(mode="json")
    return jsonify(serialized), 200


# Delete academic session
@academic_session_bp.route("/<int:session_id>", methods=["DELETE"])
@role_required(Role.ADMIN)
def delete_academic_session_route(session_id):
    deleted = delete_session(session_id, actor_id=g.user.id)
    if not deleted:
        abort(404, description="Academic session not found")

    return jsonify({"message": "Academic session deleted successfully"}), 200


# Activate academic session
@academic_session_bp.route("/<int:session_id>/activate", methods=["PATCH"])
@role_required(Role.ADMIN)
def activate_session(session_id):
    session = activate_academic_session(session_id, actor_id=g.user.id)
    if session is None:
        abort(404, description="Academic session not found")

    serialized = AcademicSessionResponse.model_validate(session).model_dump(mode="json")
    return jsonify(serialized), 200
