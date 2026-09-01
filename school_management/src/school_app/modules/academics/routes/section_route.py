from flask import Blueprint, jsonify, request, abort, g

from school_app.decorators import role_required
from school_app.utils.helpers import validate_request
from school_app.enums.role import Role

from school_app.modules.academics.requests.section_request import (
    SectionCreateRequest,
    SectionUpdateRequest,
    SectionResponse,
)

from school_app.modules.academics.services.section_service import (
    create_section,
    get_all_sections,
    get_section,
    update_section,
    delete_section,
)


section_bp = Blueprint(
    "section",
    __name__,
    url_prefix="/sections",
)


# ====================================== create_section ===============================================

@section_bp.route("/create", methods=["POST"])
@role_required(Role.ADMIN)
@validate_request(SectionCreateRequest)
def create_section_route(data: SectionCreateRequest):
    section = create_section(
        data,
        actor_id=g.user.id,
    )

    serialized = SectionResponse.model_validate(
        section
    ).model_dump()

    return jsonify(serialized), 201


# ====================================== get_all_sections ===============================================

@section_bp.route("", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER)
def get_all_sections_route():
    level_id = request.args.get(
        "level_id",
        None,
        type=int,
    )

    search = request.args.get(
        "search",
        "",
        type=str,
    )

    include_inactive = request.args.get(
        "include_inactive",
        False,
        type=bool,
    )

    page = request.args.get(
        "page",
        1,
        type=int,
    )

    per_page = request.args.get(
        "per_page",
        10,
        type=int,
    )

    result = get_all_sections(
        level_id=level_id,
        search=search,
        include_inactive=include_inactive,
        page=page,
        per_page=per_page,
        school_id=g.user.school_id,
    )

    return jsonify({
        "items": [
            SectionResponse.model_validate(item).model_dump()
            for item in result.items
        ],
        "page": result.page,
        "pages": result.pages,
        "total": result.total,
    }), 200


# ====================================== get_section ===============================================

@section_bp.route("/<int:section_id>", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER)
def get_section_route(section_id):
    section = get_section(
        section_id,
        school_id=g.user.school_id,
    )

    if section is None:
        abort(
            404,
            description="Section not found",
        )

    serialized = SectionResponse.model_validate(
        section
    ).model_dump()

    return jsonify(serialized), 200


# ====================================== update_section ===============================================

@section_bp.route(
    "/<int:section_id>/edit",
    methods=["PUT", "PATCH"],
)
@role_required(Role.ADMIN)
@validate_request(SectionUpdateRequest)
def update_section_route(
    data: SectionUpdateRequest,
    section_id,
):
    section = update_section(
        data,
        section_id,
        actor_id=g.user.id,
    )

    if section is None:
        abort(
            404,
            description="Section not found",
        )

    serialized = SectionResponse.model_validate(
        section
    ).model_dump()

    return jsonify(serialized), 200


# ====================================== delete_section ===============================================

@section_bp.route(
    "/<int:section_id>",
    methods=["DELETE"],
)
@role_required(Role.ADMIN)
def delete_section_route(section_id):
    deleted = delete_section(
        section_id,
        actor_id=g.user.id,
    )

    if not deleted:
        abort(
            404,
            description="Section not found",
        )

    return jsonify({
        "message": "Section deleted successfully"
    }), 200