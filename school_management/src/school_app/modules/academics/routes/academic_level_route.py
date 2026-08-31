from flask import Blueprint, jsonify, request, abort, g
from flask_jwt_extended import get_jwt
from school_app.decorators import role_required
from school_app.utils.helpers import validate_request
from school_app.enums.role import Role

from school_app.modules.academics.requests.academic_level_request import (
    AcademicLevelCreateRequest,
    AcademicLevelUpdateRequest,
    AcademicLevelResponse,
)

from school_app.modules.academics.services.academic_level_service import (
    create_academic_level,
    get_all_academic_levels,
    get_academic_level,
    update_academic_level,
    delete_academic_level,
)

academic_level_bp = Blueprint("academic_level", __name__, url_prefix="/academic-levels")


# ====================================== create_academic_level ===============================================

@academic_level_bp.route("/create", methods=["POST"])
@role_required(Role.ADMIN)
@validate_request(AcademicLevelCreateRequest)
def create_level(data: AcademicLevelCreateRequest):
    level = create_academic_level(data, actor_id=g.user.id)
    serialized = AcademicLevelResponse.model_validate(level).model_dump()
    return jsonify(serialized), 201


# ====================================== get_all_academic_levels ===============================================

@academic_level_bp.route("", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER)
def get_all_levels():
    claims = get_jwt()
    school_id = claims.get("school_id")  # Extracted straight from JWT payload

    stage_id = request.args.get("stage_id", None, type=int)
    search = request.args.get("search", "", type=str)
    include_inactive = request.args.get("include_inactive", False, type=bool)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    result = get_all_academic_levels(
        school_id=school_id,
        stage_id=stage_id,
        search=search,
        include_inactive=include_inactive,
        page=page,
        per_page=per_page,
    )

    return jsonify({
        "items": [AcademicLevelResponse.model_validate(item).model_dump() for item in result.items],
        "page": result.page,
        "pages": result.pages,
        "total": result.total,
    }), 200


# ====================================== get_academic_level ===============================================

@academic_level_bp.route("/<int:level_id>", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER)
def get_level(level_id):
    level = get_academic_level(level_id)
    if level is None:
        abort(404, description="Academic level not found")

    serialized = AcademicLevelResponse.model_validate(level).model_dump()
    return jsonify(serialized), 200


# ====================================== update_academic_level ===============================================

@academic_level_bp.route("/<int:level_id>/edit", methods=["PUT", "PATCH"])
@role_required(Role.ADMIN)
@validate_request(AcademicLevelUpdateRequest)
def update_level(data: AcademicLevelUpdateRequest, level_id):
    level = update_academic_level(data, level_id, actor_id=g.user.id)
    if level is None:
        abort(404, description="Academic level not found")

    serialized = AcademicLevelResponse.model_validate(level).model_dump()
    return jsonify(serialized), 200


# ====================================== delete_academic_level ===============================================

@academic_level_bp.route("/<int:level_id>", methods=["DELETE"])
@role_required(Role.ADMIN)
def delete_level_route(level_id):
    deleted = delete_academic_level(level_id, actor_id=g.user.id)
    if not deleted:
        abort(404, description="Academic level not found")

    return jsonify({"message": "Academic level deleted successfully"}), 200