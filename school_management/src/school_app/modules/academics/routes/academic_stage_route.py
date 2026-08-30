from flask import Blueprint, jsonify, request, abort, g
from school_app.decorators import role_required
from school_app.utils.helpers import validate_request
from school_app.enums.role import Role

from school_app.modules.academics.requests.academic_stage_request import (
    AcademicStageCreateRequest,
    AcademicStageUpdateRequest,
    AcademicStageResponse,
)

from school_app.modules.academics.services.academic_stage_service import (
    create_academic_stage,
    get_all_academic_stages,
    get_academic_stage,
    update_academic_stage,
    delete_academic_stage,
)

academic_stage_bp = Blueprint("academic_stage", __name__, url_prefix="/academic-stages")


# ====================================== create_academic_stage ===============================================

@academic_stage_bp.route("/create", methods=["POST"])
@role_required(Role.ADMIN)
@validate_request(AcademicStageCreateRequest)
def create_stage(data: AcademicStageCreateRequest):
    stage = create_academic_stage(data, actor_id=g.user.id)
    serialized = AcademicStageResponse.model_validate(stage).model_dump()
    return jsonify(serialized), 201


# ====================================== get_all_academic_stages ===============================================

@academic_stage_bp.route("", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER)
def get_all_stages():
    search = request.args.get("search", "", type=str)
    include_inactive = request.args.get("include_inactive", False, type=bool)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    result = get_all_academic_stages(
        search=search, include_inactive=include_inactive, page=page, per_page=per_page
    )

    return jsonify({
        "items": [AcademicStageResponse.model_validate(item).model_dump() for item in result.items],
        "page": result.page,
        "pages": result.pages,
        "total": result.total,
    }), 200


# ====================================== get_academic_stage ===============================================

@academic_stage_bp.route("/<int:stage_id>", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER)
def get_stage(stage_id):
    stage = get_academic_stage(stage_id)
    if stage is None:
        abort(404, description="Academic stage not found")

    serialized = AcademicStageResponse.model_validate(stage).model_dump()
    return jsonify(serialized), 200


# ====================================== update_academic_stage ===============================================

@academic_stage_bp.route("/<int:stage_id>/edit", methods=["PUT", "PATCH"])
@role_required(Role.ADMIN)
@validate_request(AcademicStageUpdateRequest)
def update_stage(data: AcademicStageUpdateRequest, stage_id):
    stage = update_academic_stage(data, stage_id, actor_id=g.user.id)
    if stage is None:
        abort(404, description="Academic stage not found")

    serialized = AcademicStageResponse.model_validate(stage).model_dump()
    return jsonify(serialized), 200


# ====================================== delete_academic_stage ===============================================

@academic_stage_bp.route("/<int:stage_id>", methods=["DELETE"])
@role_required(Role.ADMIN)
def delete_stage_route(stage_id):
    deleted = delete_academic_stage(stage_id, actor_id=g.user.id)
    if not deleted:
        abort(404, description="Academic stage not found")

    return jsonify({"message": "Academic stage deleted successfully"}), 200