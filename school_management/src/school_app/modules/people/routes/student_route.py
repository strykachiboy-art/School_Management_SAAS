from flask import Blueprint, jsonify, request, abort, g
from school_app.enums.role import Role
from school_app.decorators import role_required
from school_app.utils.helpers import validate_request
from school_app.modules.people.requests.student_request import StudentCreateRequest, StudentResponse

from school_app.modules.people.services.student_service import (
    create_students,
    get_all_students,
    get_student_by_id,
    update_student as update_student_service,
    delete_student as delete_student_service,
    search_student_info,
    filter_classroom_id,
    filter_admission_number,
    paginate_students,
    add_student_to_classroom,
    delete_student_from_classroom
)

student_bp = Blueprint("student", __name__, url_prefix="/students")


# ====================================== create_student ===============================================

@student_bp.route("/create", methods=["POST"])
@role_required(Role.ADMIN)
@validate_request(StudentCreateRequest)
def create_student(data: StudentCreateRequest):
    student = create_students(data, school_id=g.user.school_id, actor_id=g.user.id)
    
    serialized_student = StudentResponse.model_validate(student).model_dump()
    return jsonify(serialized_student), 201


# ====================================== get_all_student ===============================================

@student_bp.route("", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER)
def get_all_student():
    search = request.args.get("search", "", type=str)
    classroom_id = request.args.get("classroom_id", None, type=int)
    admission_number = request.args.get("admission_number", None, type=str)

    if request.args.get("paginate") == "true":
        page = paginate_students(g.user.school_id)
        return jsonify({
            "items": [StudentResponse.model_validate(item).model_dump() for item in page.items],
            "page": page.page,
            "pages": page.pages,
            "total": page.total,
        }), 200
    elif search:
        students = search_student_info(search, g.user.school_id)
    elif classroom_id:
        students = filter_classroom_id(classroom_id, g.user.school_id)
    elif admission_number:
        students = filter_admission_number(admission_number, g.user.school_id)
    else:
        students = get_all_students(g.user.school_id)

    serialized_students = [StudentResponse.model_validate(s).model_dump() for s in students]
    return jsonify(serialized_students), 200


# ====================================== get_student ===============================================

@student_bp.route("/<int:student_id>", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER, Role.STUDENT)
def get_student(student_id):
    student = get_student_by_id(student_id, g.user.school_id)
    if student is None:
        abort(404, description="Student not found")

    serialized_student = StudentResponse.model_validate(student).model_dump()
    return jsonify(serialized_student), 200


# ====================================== update_student ===============================================

@student_bp.route("/<int:student_id>/edit", methods=["PUT", "PATCH"])
@role_required(Role.ADMIN, Role.TEACHER, Role.STUDENT)
@validate_request(StudentCreateRequest)
def update_student(data: StudentCreateRequest, student_id):
    updated_student = update_student_service(student_id, data, school_id=g.user.school_id, actor_id=g.user.id)
    if updated_student is None:
        abort(404, description="Student not found")

    serialized_student = StudentResponse.model_validate(updated_student).model_dump()
    return jsonify(serialized_student), 200


# ====================================== delete_student ===============================================

@student_bp.route("/<int:student_id>", methods=["DELETE"])
@role_required(Role.ADMIN)
def delete_student(student_id):
    deleted = delete_student_service(student_id, school_id=g.user.school_id, actor_id=g.user.id)

    if not deleted:
        abort(404, description="Student not found")

    return jsonify({"message": "Student deleted successfully"}), 200



# ====================================== add_student_to_classroom ===============================================

@student_bp.route("/<int:student_id>/classroom/<int:classroom_id>", methods=["PATCH"])
@role_required(Role.ADMIN)
def add_to_classroom(student_id, classroom_id):
    student = add_student_to_classroom(student_id, classroom_id, g.user.school_id)
    if student is None:
        abort(404, description="Student not found")

    serialized_student = StudentResponse.model_validate(student).model_dump()
    return jsonify(serialized_student), 200


# ====================================== remove_student_from_classroom ===============================================

@student_bp.route("/<int:student_id>/classroom", methods=["DELETE"])
@role_required(Role.ADMIN)
def remove_from_classroom(student_id):
    student = delete_student_from_classroom(student_id, g.user.school_id)
    if student is None:
        abort(404, description="Student not found")

    serialized_student = StudentResponse.model_validate(student).model_dump()
    return jsonify(serialized_student), 200