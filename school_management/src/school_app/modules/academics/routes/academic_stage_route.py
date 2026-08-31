# src/school_app/modules/academics/routes/academic_stage_route.py

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


@academic_stage_bp.route("/create", methods=["POST"])
@role_required(Role.ADMIN)
@validate_request(AcademicStageCreateRequest)
def create_stage(data: AcademicStageCreateRequest):
    # Derive school_id from authenticated user if not provided
    if getattr(data, "school_id", None) is None:
        data.school_id = getattr(g.user, "school_id", None)

    if data.school_id is None:
        abort(400, description="Missing required field: school_id")

    # Normalize code: prefer explicit string code, else convert numeric code to string
    if getattr(data, "code", None) is None and getattr(data, "num_code", None) is not None:
        data.code = str(data.num_code)

    stage = create_academic_stage(data, actor_id=g.user.id)
    serialized = AcademicStageResponse.model_validate(stage).model_dump(mode="json")
    return jsonify(serialized), 201


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
        "items": [AcademicStageResponse.model_validate(item).model_dump(mode="json") for item in result.items],
        "page": result.page,
        "pages": result.pages,
        "total": result.total,
    }), 200


@academic_stage_bp.route("/<int:stage_id>", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER)
def get_stage(stage_id):
    stage = get_academic_stage(stage_id)
    if stage is None:
        abort(404, description="Academic stage not found")

    serialized = AcademicStageResponse.model_validate(stage).model_dump(mode="json")
    return jsonify(serialized), 200


@academic_stage_bp.route("/<int:stage_id>/edit", methods=["PUT", "PATCH"])
@role_required(Role.ADMIN)
@validate_request(AcademicStageUpdateRequest)
def update_stage(data: AcademicStageUpdateRequest, stage_id):
    # If update payload omits school_id, derive from actor for consistency
    if getattr(data, "school_id", None) is None:
        data.school_id = getattr(g.user, "school_id", None)

    # Normalize code if numeric provided
    if getattr(data, "code", None) is None and getattr(data, "num_code", None) is not None:
        data.code = str(data.num_code)

    stage = update_academic_stage(data, stage_id, actor_id=g.user.id)
    if stage is None:
        abort(404, description="Academic stage not found")

    serialized = AcademicStageResponse.model_validate(stage).model_dump(mode="json")
    return jsonify(serialized), 200


@academic_stage_bp.route("/<int:stage_id>", methods=["DELETE"])
@role_required(Role.ADMIN)
def delete_stage_route(stage_id):
    deleted = delete_academic_stage(stage_id, actor_id=g.user.id)
    if not deleted:
        abort(404, description="Academic stage not found")

    return jsonify({"message": "Academic stage deleted successfully"}), 200
