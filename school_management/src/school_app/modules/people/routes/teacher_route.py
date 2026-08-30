from flask import Blueprint, jsonify, request, abort, g
from school_app.decorators import role_required
from school_app.enums.role import Role
from school_app.utils.helpers import validate_request
from school_app.modules.people.requests.teacher_request import TeacherCreateRequest, TeacherResponse
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
    get_classroom, serialize_classroom
)

teacher_bp = Blueprint("teacher", __name__, url_prefix="/teachers")


# ====================================== create_teacher ===============================================

@teacher_bp.route("/create", methods=["POST"])
@role_required(Role.ADMIN)
@validate_request(TeacherCreateRequest)
def create_teacher(data: TeacherCreateRequest):
    teacher = create_teachers(data, actor_id=g.user.id)
    
    serialized_teacher = TeacherResponse.model_validate(teacher).model_dump()
    return jsonify(serialized_teacher), 201


# ====================================== get_all_teacher ===============================================

@teacher_bp.route("", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER, Role.STUDENT)
def get_all_teacher():
    search = request.args.get("search", "", type=str)
    teacher_id = request.args.get("id", None, type=int)
    user_id = request.args.get("user_id", None, type=int)

    if request.args.get("paginate") == "true":
        page = paginate_teachers()
        return jsonify({
            "items": [TeacherResponse.model_validate(item).model_dump() for item in page.items],
            "page": page.page,
            "pages": page.pages,
            "total": page.total,
        }), 200
    elif search:
        teacher = search_teacher_info(search)
    elif teacher_id or user_id:
        filters = {}
        if teacher_id:
            filters["id"] = teacher_id
        if user_id:
            filters["user_id"] = user_id
        teacher = filter_Teacher(**filters)
    else:
        teacher = get_all_teachers()

    serialized_teachers = [TeacherResponse.model_validate(t).model_dump() for t in teacher]
    return jsonify(serialized_teachers), 200


# ====================================== get_teacher ===============================================

@teacher_bp.route("/<int:teacher_id>", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER, Role.STUDENT)
def get_teacher(teacher_id):
    teacher = get_teacher_by_id(teacher_id)
    if teacher is None:
        abort(404, description="Teacher not found")

    serialized_teacher = TeacherResponse.model_validate(teacher).model_dump()
    return jsonify(serialized_teacher), 200


# ====================================== update_teacher ===============================================

@teacher_bp.route("/<int:teacher_id>/edit", methods=["PUT", "PATCH"])
@role_required(Role.ADMIN)
@validate_request(TeacherCreateRequest)
def update_teacher(data: TeacherCreateRequest, teacher_id):
    teacher = get_teacher_by_id(teacher_id)
    if teacher is None:
        abort(404, description="Teacher not found")

    updated_teacher = update_teacher_service(teacher_id, data, actor_id=g.user.id)

    serialized_teacher = TeacherResponse.model_validate(updated_teacher).model_dump()
    return jsonify(serialized_teacher), 200


# ====================================== delete_teacher ===============================================

@teacher_bp.route("/<int:teacher_id>", methods=["DELETE"])
@role_required(Role.ADMIN)
def delete_teacher(teacher_id):
    deleted = delete_teacher_service(teacher_id, actor_id=g.user.id)

    if not deleted:
        abort(404, description="Teacher not found")

    return jsonify({"message": "Teacher deleted successfully"}), 200


# ====================================== get_classroom_details ===============================================

@teacher_bp.route("/classrooms/<int:classroom_id>", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER, Role.STUDENT)
def get_classroom_details(classroom_id):
    classroom = get_classroom(classroom_id)
    if classroom is None:
        abort(404, description="Classroom not found")

    return jsonify(serialize_classroom(classroom)), 200