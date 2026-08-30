from flask import Blueprint, jsonify, request, abort, g
from school_app.decorators import role_required
from school_app.enums.role import Role
from school_app.modules.classrooms.requests.subject_request import SubjectResponse
from school_app.modules.classrooms.services.assignment_service import (
    assign_subject_to_teachers,
    remove_subject_from_teachers,
    get_subjects_for_teacher,
    assign_subject_to_students,
    remove_subject_from_students,
    get_subjects_for_student,
    assign_subject_to_classrooms,
    remove_subject_from_classrooms,
    get_subjects_for_classroom,
)

ass_bp = Blueprint("assignment", __name__, url_prefix="/assignments")


def _get_ids_from_request(key):
    data = request.get_json(silent=True) or {}
    ids = data.get(key)

    if not ids or not isinstance(ids, list):
        abort(400, description=f"Request body must include a non-empty '{key}' list.")

    return ids


# ====================================== Teacher assignment routes ===============================================
@ass_bp.route("/subjects/<int:subject_id>/assign/teachers", methods=["POST"])
@role_required(Role.ADMIN)
def assign_subject_to_teachers_route(subject_id):
    teacher_ids = _get_ids_from_request("teacher_ids")

    try:
        assign_subject_to_teachers(subject_id, teacher_ids, actor_id=g.user.id)
    except ValueError as e:
        abort(400, description=str(e))

    return jsonify({"message": "Subject assigned to teachers successfully"}), 200


# ====================================== remove_subject_from_teachers_route ===============================================

@ass_bp.route("/subjects/<int:subject_id>/remove/teachers", methods=["DELETE"])
@role_required(Role.ADMIN)
def remove_subject_from_teachers_route(subject_id):
    teacher_ids = _get_ids_from_request("teacher_ids")

    try:
        remove_subject_from_teachers(subject_id, teacher_ids, actor_id=g.user.id)
    except ValueError as e:
        abort(400, description=str(e))

    return jsonify({"message": "Subject removed from teachers successfully"}), 200


# ====================================== get_teacher_subjects_route ===============================================

@ass_bp.route("/teachers/<int:teacher_id>/subjects", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER)
def get_teacher_subjects_route(teacher_id):
    try:
        subjects = get_subjects_for_teacher(teacher_id)
    except ValueError as e:
        abort(404, description=str(e))

    serialized_subjects = [SubjectResponse.model_validate(s).model_dump() for s in subjects]
    return jsonify(serialized_subjects), 200


# ====================================== assign_subject_to_students_route ===============================================

@ass_bp.route("/subjects/<int:subject_id>/assign/students", methods=["POST"])
@role_required(Role.ADMIN)
def assign_subject_to_students_route(subject_id):
    student_ids = _get_ids_from_request("student_ids")

    try:
        assign_subject_to_students(subject_id, student_ids, actor_id=g.user.id)
    except ValueError as e:
        abort(400, description=str(e))

    return jsonify({"message": "Subject assigned to students successfully"}), 200


# ====================================== remove_subject_from_students_route ===============================================

@ass_bp.route("/subjects/<int:subject_id>/remove/students", methods=["DELETE"])
@role_required(Role.ADMIN)
def remove_subject_from_students_route(subject_id):
    student_ids = _get_ids_from_request("student_ids")

    try:
        remove_subject_from_students(subject_id, student_ids, actor_id=g.user.id)
    except ValueError as e:
        abort(400, description=str(e))

    return jsonify({"message": "Subject removed from students successfully"}), 200


@ass_bp.route("/students/<int:student_id>/subjects", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER, Role.STUDENT)
def get_student_subjects_route(student_id):
    try:
        subjects = get_subjects_for_student(student_id)
    except ValueError as e:
        abort(404, description=str(e))

    serialized_subjects = [SubjectResponse.model_validate(s).model_dump() for s in subjects]
    return jsonify(serialized_subjects), 200


# ====================================== Classroom assignment routes ===============================================

@ass_bp.route("/subjects/<int:subject_id>/assign/classrooms", methods=["POST"])
@role_required(Role.ADMIN)
def assign_subject_to_classrooms_route(subject_id):
    classroom_ids = _get_ids_from_request("classroom_ids")

    try:
        assign_subject_to_classrooms(subject_id, classroom_ids, actor_id=g.user.id)
    except ValueError as e:
        abort(400, description=str(e))

    return jsonify({"message": "Subject assigned to classrooms successfully"}), 200

# ====================================== remove_subject_from_classrooms_route ===============================================

@ass_bp.route("/subjects/<int:subject_id>/remove/classrooms", methods=["DELETE"])
@role_required(Role.ADMIN)
def remove_subject_from_classrooms_route(subject_id):
    classroom_ids = _get_ids_from_request("classroom_ids")

    try:
        remove_subject_from_classrooms(subject_id, classroom_ids, actor_id=g.user.id)
    except ValueError as e:
        abort(400, description=str(e))

    return jsonify({"message": "Subject removed from classrooms successfully"}), 200


# ====================================== get_classroom_subjects_route ===============================================

@ass_bp.route("/classrooms/<int:classroom_id>/subjects", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER, Role.STUDENT)
def get_classroom_subjects_route(classroom_id):
    try:
        subjects = get_subjects_for_classroom(classroom_id)
    except ValueError as e:
        abort(404, description=str(e))

    serialized_subjects = [SubjectResponse.model_validate(s).model_dump() for s in subjects]
    return jsonify(serialized_subjects), 200