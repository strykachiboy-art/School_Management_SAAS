from flask import jsonify, abort
from school_app.modules.school.routes.admin_core_route import admin_bp
from school_app.models.result import Result
from school_app.modules.grading.services.grade_service import calculate_student_grade
from school_app.decorators import role_required
from school_app.enums.role import Role

@admin_bp.route("/students/<int:student_id>/grade", methods=["GET"])
@role_required(Role.ADMIN)
def get_student_grade(student_id):
    results = Result.query.filter_by(student_id=student_id).all()

    if not results:
        abort(404, description="No results found for this student")

    grade = calculate_student_grade(results)

    return jsonify({
        "student_id": student_id,
        "grade": grade
    }), 200