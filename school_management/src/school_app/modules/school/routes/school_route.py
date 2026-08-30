# App/routes/admin/school_route.py

from flask import Blueprint, jsonify, request, abort, g
from school_app.decorators import platform_admin_required
from school_app.utils.helpers import validate_request

from school_app.modules.school.requests.school_request import (
    SchoolCreateRequest,
    SchoolUpdateRequest,
    SchoolResponse,
)

from school_app.modules.school.services.school_service import (
    create_school,
    get_all_schools,
    get_school,
    get_school_by_slug,
    update_school,
    delete_school,
)

school_bp = Blueprint("school", __name__, url_prefix="/schools")


# ====================================== create_school ===============================================

@school_bp.route("/create", methods=["POST"])
@platform_admin_required
@validate_request(SchoolCreateRequest)
def create_school_route(data: SchoolCreateRequest):
    school = create_school(data, actor_id=g.user.id)
    return jsonify(SchoolResponse.model_validate(school).model_dump()), 201


# ====================================== get_all_schools ===============================================

@school_bp.route("", methods=["GET"])
@platform_admin_required
def get_all_schools_route():
    search = request.args.get("search", "", type=str)
    include_inactive = request.args.get("include_inactive", False, type=bool)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    result = get_all_schools(search=search, include_inactive=include_inactive, page=page, per_page=per_page)

    return jsonify({
        "items": [SchoolResponse.model_validate(item).model_dump() for item in result.items],
        "page": result.page,
        "pages": result.pages,
        "total": result.total,
    }), 200


# ====================================== get_school ===============================================

@school_bp.route("/<int:school_id>", methods=["GET"])
@platform_admin_required
def get_school_route(school_id):
    school = get_school(school_id)
    if school is None:
        abort(404, description="School not found")
    return jsonify(SchoolResponse.model_validate(school).model_dump()), 200


@school_bp.route("/by-slug/<string:slug>", methods=["GET"])
@platform_admin_required
def get_school_by_slug_route(slug):
    school = get_school_by_slug(slug)
    if school is None:
        abort(404, description="School not found")
    return jsonify(SchoolResponse.model_validate(school).model_dump()), 200


# ====================================== update_school ===============================================

@school_bp.route("/<int:school_id>/edit", methods=["PUT", "PATCH"])
@platform_admin_required
@validate_request(SchoolUpdateRequest)
def update_school_route(data: SchoolUpdateRequest, school_id):
    school = update_school(data, school_id, actor_id=g.user.id)
    if school is None:
        abort(404, description="School not found")
    return jsonify(SchoolResponse.model_validate(school).model_dump()), 200


# ====================================== delete_school ===============================================

@school_bp.route("/<int:school_id>", methods=["DELETE"])
@platform_admin_required
def delete_school_route(school_id):
    if not delete_school(school_id, actor_id=g.user.id):
        abort(404, description="School not found")
    return jsonify({"message": "School deleted successfully"}), 200