from flask import Blueprint, jsonify, abort, g
from flask_jwt_extended import jwt_required
from school_app.decorators import role_required
from school_app.modules.grading.services.teacher_grade_service import get_student_grade_for_teachers
from school_app.enums.role import Role

teacher_grade_bp = Blueprint("teacher_grade", __name__, url_prefix="/teacher")


@teacher_grade_bp.route("/students/<int:student_id>/grade", methods=["GET"])
@jwt_required()
@role_required(Role.TEACHER)
def get_student_grade(student_id):
    teacher = g.user.teacher_profile

    if teacher is None:
        abort(403, description="Teacher profile not found")

    try:
        grade = get_student_grade_for_teachers(teacher.id, student_id)
    except ValueError as e:
        abort(404, description=str(e))

    return jsonify({
        "student_id": student_id,
        "grade": grade
    }), 200