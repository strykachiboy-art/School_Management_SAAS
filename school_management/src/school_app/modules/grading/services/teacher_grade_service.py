from school_app.extensions import db
from school_app.models.student import Student
from school_app.models.result import Result
from school_app.modules.grading.services.grade_service import calculate_student_grade


def get_student_grade_for_teachers(teacher_id, student_id):
    student = db.session.get(Student, student_id)

    if student is None:
        raise ValueError("Student not found")

    if student.classroom is None:
        raise ValueError("Student is not assigned to a classroom")

    if student.classroom.teacher_id != teacher_id:
        raise ValueError("You are not allowed to view this student's grade")

    results = Result.query.filter_by(student_id=student_id).all()

    return calculate_student_grade(results)