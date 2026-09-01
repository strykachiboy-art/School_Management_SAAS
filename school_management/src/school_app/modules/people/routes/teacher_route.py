from flask import Blueprint, jsonify, request, abort, g

from school_app.decorators import role_required
from school_app.enums.role import Role
from school_app.utils.helpers import validate_request

from school_app.modules.people.requests.teacher_request import (
    TeacherCreateRequest,
    TeacherUpdateRequest,
    TeacherResponse,
)

from school_app.modules.people.services.teacher_service import (
    create_teachers,
    update_teachers as update_teacher_service,
    get_teacher_by_id,
    get_all_teachers,
    delete_teacher as delete_teacher_service,
    filter_Teacher,
    search_teacher_info,
    paginate_teachers,
)

from school_app.modules.classrooms.services.classroom_service import (
    get_classroom,
    serialize_classroom,
)


teacher_bp = Blueprint(
    "teacher",
    __name__,
    url_prefix="/teachers",
)


# ====================================== create_teacher ===============================================

@teacher_bp.route("/create", methods=["POST"])
@role_required(Role.ADMIN)
@validate_request(TeacherCreateRequest)
def create_teacher(data: TeacherCreateRequest):
    teacher = create_teachers(
        data,
        school_id=g.user.school_id,
        actor_id=g.user.id,
    )

    serialized_teacher = (
        TeacherResponse
        .model_validate(teacher)
        .model_dump(mode="json")
    )

    return jsonify(serialized_teacher), 201


# ====================================== get_all_teacher ===============================================

@teacher_bp.route("", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER, Role.STUDENT)
def get_all_teacher():
    school_id = g.user.school_id

    search = request.args.get("search", "", type=str)
    teacher_id = request.args.get("id", None, type=int)
    user_id = request.args.get("user_id", None, type=int)

    if request.args.get("paginate") == "true":
        page = paginate_teachers(
            school_id=school_id,
        )

        return jsonify({
            "items": [
                TeacherResponse
                .model_validate(item)
                .model_dump(mode="json")
                for item in page.items
            ],
            "page": page.page,
            "pages": page.pages,
            "total": page.total,
        }), 200

    elif search:
        teachers = search_teacher_info(
            search,
            school_id=school_id,
        )

    elif teacher_id or user_id:
        filters = {}

        if teacher_id is not None:
            filters["id"] = teacher_id

        if user_id is not None:
            filters["user_id"] = user_id

        teachers = filter_Teacher(
            school_id=school_id,
            **filters,
        )

    else:
        teachers = get_all_teachers(
            school_id=school_id,
        )

    serialized_teachers = [
        TeacherResponse
        .model_validate(teacher)
        .model_dump(mode="json")
        for teacher in teachers
    ]

    return jsonify(serialized_teachers), 200


# ====================================== get_teacher ===============================================

@teacher_bp.route("/<int:teacher_id>", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER, Role.STUDENT)
def get_teacher(teacher_id):
    teacher = get_teacher_by_id(
        teacher_id,
        school_id=g.user.school_id,
    )

    if teacher is None:
        abort(404, description="Teacher not found")

    serialized_teacher = (
        TeacherResponse
        .model_validate(teacher)
        .model_dump(mode="json")
    )

    return jsonify(serialized_teacher), 200


# ====================================== update_teacher ===============================================

@teacher_bp.route("/<int:teacher_id>/edit", methods=["PUT", "PATCH"])
@role_required(Role.ADMIN)
@validate_request(TeacherUpdateRequest)
def update_teacher(data: TeacherUpdateRequest, teacher_id):
    updated_teacher = update_teacher_service(
        teacher_id,
        data,
        school_id=g.user.school_id,
        actor_id=g.user.id,
    )

    if updated_teacher is None:
        abort(404, description="Teacher not found")

    serialized_teacher = (
        TeacherResponse
        .model_validate(updated_teacher)
        .model_dump(mode="json")
    )

    return jsonify(serialized_teacher), 200


# ====================================== delete_teacher ===============================================

@teacher_bp.route("/<int:teacher_id>", methods=["DELETE"])
@role_required(Role.ADMIN)
def delete_teacher(teacher_id):
    deleted = delete_teacher_service(
        teacher_id,
        school_id=g.user.school_id,
        actor_id=g.user.id,
    )

    if not deleted:
        abort(404, description="Teacher not found")

    return jsonify({
        "message": "Teacher deleted successfully"
    }), 200


# ====================================== get_classroom_details ===============================================

@teacher_bp.route("/classrooms/<int:classroom_id>", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER, Role.STUDENT)
def get_classroom_details(classroom_id):
    classroom = get_classroom(classroom_id)

    if classroom is None:
        abort(404, description="Classroom not found")

    return jsonify(
        serialize_classroom(classroom)
    ), 200