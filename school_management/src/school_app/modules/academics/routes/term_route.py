from flask import Blueprint, jsonify, request, abort, g
from school_app.enums.role import Role
from school_app.decorators import role_required
from school_app.utils.helpers import validate_request

from school_app.modules.academics.requests.term_request import (
    TermResponse,
    TermCreateRequest,
    TermUpdateRequest,
    TermReassignSessionRequest,
)

from school_app.modules.academics.services.term_service import (
    create_term,
    get_all_term,
    get_term_by_id,
    update_term,
    reassign_term_session,
    delete_term,
    activate_term,
)

term_bp = Blueprint("term", __name__, url_prefix="/terms")


# ====================================== Create Term ===============================================

@term_bp.route("/create", methods=["POST"])
@role_required(Role.ADMIN)
@validate_request(TermCreateRequest)
def create_term_route(data: TermCreateRequest):
    term = create_term(data, school_id=g.user.school_id, actor_id=g.user.id)
    serialized = TermResponse.model_validate(term).model_dump()
    return jsonify(serialized), 201


# ====================================== Get All Terms ===============================================

@term_bp.route("", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER)
def get_all_terms_route():
    search = request.args.get("search", "", type=str)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    result = get_all_term(school_id=g.user.school_id, search=search, page=page, per_page=per_page)

    return jsonify({
        "items": [TermResponse.model_validate(item).model_dump() for item in result.items],
        "page": result.page,
        "pages": result.pages,
        "total": result.total,
    }), 200


# ====================================== Get Term ===============================================

@term_bp.route("/<int:term_id>", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER)
def get_term_route(term_id: int):
    term = get_term_by_id(term_id, school_id=g.user.school_id)
    if term is None:
        abort(404, description="Term not found")

    serialized = TermResponse.model_validate(term).model_dump()
    return jsonify(serialized), 200


# ====================================== Update Term Details ===============================================

@term_bp.route("/<int:term_id>/edit", methods=["PUT", "PATCH"])
@role_required(Role.ADMIN)
@validate_request(TermUpdateRequest)
def update_term_route(data: TermUpdateRequest, term_id: int):
    term = update_term(data, term_id, school_id=g.user.school_id, actor_id=g.user.id)
    if term is None:
        abort(404, description="Term not found")

    serialized = TermResponse.model_validate(term).model_dump()
    return jsonify(serialized), 200


# ====================================== Reassign Academic Session ===============================================

@term_bp.route("/<int:term_id>/reassign-session", methods=["PATCH", "POST"])
@role_required(Role.ADMIN)
@validate_request(TermReassignSessionRequest)
def reassign_term_session_route(data: TermReassignSessionRequest, term_id: int):
    term = reassign_term_session(
        term_id, data.academic_session_id, school_id=g.user.school_id, actor_id=g.user.id
    )
    if term is None:
        abort(404, description="Term not found")

    serialized = TermResponse.model_validate(term).model_dump()
    return jsonify(serialized), 200


# ====================================== Delete Term ===============================================

@term_bp.route("/<int:term_id>", methods=["DELETE"])
@role_required(Role.ADMIN)
def delete_term_route(term_id: int):
    deleted = delete_term(term_id, school_id=g.user.school_id, actor_id=g.user.id)
    if not deleted:
        abort(404, description="Term not found")

    return jsonify({"message": "Term deleted successfully"}), 200


# ====================================== Activate Term ===============================================

@term_bp.route("/<int:term_id>/activate", methods=["PATCH"])
@role_required(Role.ADMIN)
def activate_term_route(term_id: int):
    term = activate_term(term_id, school_id=g.user.school_id, actor_id=g.user.id)
    if term is None:
        abort(404, description="Term not found")

    serialized = TermResponse.model_validate(term).model_dump()
    return jsonify(serialized), 200