from flask import Blueprint, jsonify, request, abort, g

from school_app.decorators import role_required
from school_app.utils.helpers import validate_request
from school_app.enums.role import Role

from school_app.modules.classrooms.requests.classroom_request import (
    ClassroomCreateRequest,
    ClassroomResponse,
    BulkAssignStudentsRequest,
)

from school_app.modules.classrooms.services.classroom_service import (
    create_classroom,
    get_all_classrooms,
    get_classroom,
    get_all_classroom_list,
    update_classroom as update_classroom_service,
    delete_classroom as delete_classroom_service,
    bulk_assign_students as bulk_assign_students_service,
)


classroom_bp = Blueprint(
    "classroom",
    __name__,
    url_prefix="/classrooms",
)


# ======================================
# Create Classroom
# ======================================

@classroom_bp.route("/create", methods=["POST"])
@role_required(Role.ADMIN)
@validate_request(ClassroomCreateRequest)
def create_classroom_route(data: ClassroomCreateRequest):

    classroom = create_classroom(
        data=data,
        school_id=g.user.school_id,
        actor_id=g.user.id,
    )

    if classroom is None:
        abort(400, description="Could not create classroom")

    serialized_classroom = (
        ClassroomResponse
        .model_validate(classroom)
        .model_dump()
    )

    return jsonify(serialized_classroom), 201


# ======================================
# Get All Classrooms
# ======================================

@classroom_bp.route("", methods=["GET"])
@role_required(
    Role.ADMIN,
    Role.TEACHER,
    Role.STUDENT,
)
def get_all_classrooms_route():

    school_id = g.user.school_id

    if request.args.get("list") == "true":

        classrooms = get_all_classroom_list(
            school_id=school_id
        )

        serialized_list = [
            ClassroomResponse
            .model_validate(classroom)
            .model_dump()
            for classroom in classrooms
        ]

        return jsonify(serialized_list), 200

    page = get_all_classrooms(
        school_id=school_id,
        search=request.args.get(
            "search",
            "",
            type=str,
        ),
        page=request.args.get(
            "page",
            1,
            type=int,
        ),
        per_page=request.args.get(
            "per_page",
            10,
            type=int,
        ),
    )

    return jsonify({
        "items": [
            ClassroomResponse
            .model_validate(item)
            .model_dump()
            for item in page.items
        ],
        "page": page.page,
        "pages": page.pages,
        "total": page.total,
    }), 200


# ======================================
# Get Classroom Detail
# ======================================

@classroom_bp.route("/<int:classroom_id>", methods=["GET"])
@role_required(
    Role.ADMIN,
    Role.TEACHER,
    Role.STUDENT,
)
def get_classroom_detail(classroom_id):

    classroom = get_classroom(
        classroom_id=classroom_id,
        school_id=g.user.school_id,
    )

    if classroom is None:
        abort(
            404,
            description="Classroom not found",
        )

    serialized_classroom = (
        ClassroomResponse
        .model_validate(classroom)
        .model_dump()
    )

    return jsonify(serialized_classroom), 200


# ======================================
# Update Classroom
# ======================================

@classroom_bp.route(
    "/<int:classroom_id>/edit",
    methods=["PUT", "PATCH"],
)
@role_required(Role.ADMIN)
@validate_request(ClassroomCreateRequest)
def update_classroom_route(
    data: ClassroomCreateRequest,
    classroom_id,
):

    classroom = get_classroom(
        classroom_id=classroom_id,
        school_id=g.user.school_id,
    )

    if classroom is None:
        abort(
            404,
            description="Classroom not found",
        )

    updated_classroom = update_classroom_service(
        classroom_id=classroom_id,
        data=data,
        school_id=g.user.school_id,
        actor_id=g.user.id,
    )

    serialized_classroom = (
        ClassroomResponse
        .model_validate(updated_classroom)
        .model_dump()
    )

    return jsonify(serialized_classroom), 200


# ======================================
# Bulk Assign Students
# ======================================

@classroom_bp.route(
    "/<int:classroom_id>/students/bulk",
    methods=["POST"],
)
@role_required(Role.ADMIN)
@validate_request(BulkAssignStudentsRequest)
def bulk_assign_students_route(
    data: BulkAssignStudentsRequest,
    classroom_id,
):

    result = bulk_assign_students_service(
        classroom_id=classroom_id,
        student_ids=data.student_ids,
        school_id=g.user.school_id,
        actor_id=g.user.id,
    )

    if result is None:
        abort(
            404,
            description="Classroom not found",
        )

    return jsonify(result), 200


# ======================================
# Delete Classroom
# ======================================

@classroom_bp.route(
    "/<int:classroom_id>",
    methods=["DELETE"],
)
@role_required(Role.ADMIN)
def delete_classroom_route(classroom_id):

    deleted = delete_classroom_service(
        classroom_id=classroom_id,
        school_id=g.user.school_id,
        actor_id=g.user.id,
    )

    if not deleted:
        abort(
            404,
            description="Classroom not found",
        )

    return jsonify({
        "message": "Classroom deleted successfully"
    }), 200