import pytest
from school_app.extensions import db
from school_app.models.result import Result

JSON_HEADERS = {"Accept": "application/json"}


@pytest.fixture
def results_for_student(student, exam, subject, classroom):
    """Two results for the same student across two different exams."""
    from school_app.models.exam import Exam
    from datetime import date, time

    exam2 = Exam(
        title="Second Exam",
        description="Second test exam",
        subject_id=subject.id,
        classroom_id=classroom.id,
        session_id=exam.session_id,
        exam_date=date(2026, 12, 20),
        start_time=time(11, 0),
        duration_minutes=90,
        total_marks=100,
    )
    db.session.add(exam2)
    db.session.commit()

    r1 = Result(student_id=student.id, exam_id=exam.id, marks_obtained=80)
    r2 = Result(student_id=student.id, exam_id=exam2.id, marks_obtained=60)
    db.session.add_all([r1, r2])
    db.session.commit()
    return [r1, r2]


def test_get_student_grade_success(client, admin_headers, student, results_for_student):
    response = client.get(f"/admin/students/{student.id}/grade", headers=admin_headers)
    assert response.status_code == 200

    data = response.get_json()
    assert data["student_id"] == student.id
    assert data["grade"]["total"] == 140
    assert data["grade"]["average"] == pytest.approx(70.0)
    assert data["grade"]["grade"] == "A"
    assert data["grade"]["remark"] == "Excelent"


def test_get_student_grade_no_results_404(client, admin_headers, student):
    response = client.get(f"/admin/students/{student.id}/grade", headers=admin_headers)
    assert response.status_code == 404


def test_get_student_grade_requires_admin_role(client, student):
    # no auth header at all
    response = client.get(f"/admin/students/{student.id}/grade")
    assert response.status_code in (401, 403)