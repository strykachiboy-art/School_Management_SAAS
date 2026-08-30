from flask import jsonify, abort, g, Blueprint, request
from flask_jwt_extended import jwt_required
from school_app.decorators import role_required
from school_app.modules.grading.services.student_grade_service import get_student_own_grade
from school_app.enums.role import Role

student_grade_bp = Blueprint("student_grade", __name__, url_prefix="/student")


@student_grade_bp.route("/me/grade", methods=["GET"])
@jwt_required()
@role_required(Role.STUDENT)
def get_my_grade_route():
    student = g.user.student_profile
    if student is None:
        abort(403, description="Student profile not found")

    term_id = request.args.get("term_id", type=int)

    try:
        grade = get_student_own_grade(student.id, term_id=term_id)
    except ValueError as e:
        abort(404, description=str(e))

    return jsonify({
        "average": grade["average"],
        "grade": grade["grade"],
        "remark": grade["remark"]
    }), 200