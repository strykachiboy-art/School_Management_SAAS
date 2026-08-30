# test/test_teacher_grade_service.py

import pytest
from school_app.extensions import db
from school_app.models.result import Result
from school_app.modules.grading.services.teacher_grade_service import get_student_grade_for_teachers

JSON_HEADERS = {"Accept": "application/json"}

def test_get_student_grade_for_teachers_success(app, teacher, classroom, student, exam):
    with app.app_context():
        db.session.add(classroom)
        db.session.add(student)
        classroom.teacher_id = teacher.id
        student.classroom_id = classroom.id
        db.session.commit()

        result = Result(student_id=student.id, exam_id=exam.id, marks_obtained=90)
        db.session.add(result)
        db.session.commit()

        grade = get_student_grade_for_teachers(teacher.id, student.id)

        assert grade["total"] == 90
        assert grade["average"] == pytest.approx(90.0)
        assert grade["grade"] == "A"
        assert grade["remark"] == "Excelent"


def test_get_student_grade_for_teachers_no_results(app, teacher, classroom, student):
    """Student is legitimately in the teacher's classroom but has no results yet."""
    with app.app_context():
        db.session.add(classroom)
        db.session.add(student)
        classroom.teacher_id = teacher.id
        student.classroom_id = classroom.id
        db.session.commit()

        grade = get_student_grade_for_teachers(teacher.id, student.id)

        assert grade["total"] == 0
        assert grade["average"] == 0
        assert grade["grade"] == "F"


def test_get_student_grade_for_teachers_student_not_found(app, teacher):
    with app.app_context():
        with pytest.raises(ValueError, match="Student not found"):
            get_student_grade_for_teachers(teacher.id, 9999)


def test_get_student_grade_for_teachers_no_classroom(app, teacher, student):
    """Student exists but classroom_id was never set."""
    with app.app_context():
        with pytest.raises(ValueError, match="not assigned to a classroom"):
            get_student_grade_for_teachers(teacher.id, student.id)


def test_get_student_grade_for_teachers_wrong_teacher(app, teacher, teacher2, classroom, student):
    """Student belongs to `teacher`'s classroom; `teacher2` tries to access it."""
    with app.app_context():
        db.session.add(classroom)
        db.session.add(student)
        classroom.teacher_id = teacher.id
        student.classroom_id = classroom.id
        db.session.commit()

        with pytest.raises(ValueError, match="not allowed to view"):
            get_student_grade_for_teachers(teacher2.id, student.id)