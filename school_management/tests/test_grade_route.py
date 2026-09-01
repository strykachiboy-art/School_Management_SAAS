from datetime import date, time

import pytest

from school_app.extensions import db
from school_app.models.result import Result


@pytest.fixture
def results_for_student(
    student,
    exam,
    make_exam,
    subject,
    classroom,
    academic_session,
    term,
):
    """
    Create two results for the same student across two different exams.

    The second exam is created through the shared make_exam fixture so that
    school_id, term_id, session_id, and all other required tenant-aware
    fields are populated consistently.
    """

    exam2 = make_exam(
        suffix="2",
        subject_obj=subject,
        classroom_obj=classroom,
        session_obj=academic_session,
        term_obj=term,
        exam_date_val=date(2026, 12, 20),
        start_time_val=time(11, 0),
        duration_minutes=90,
        total_marks=100,
    )

    result1 = Result(
        school_id=student.school_id,
        student_id=student.id,
        exam_id=exam.id,
        marks_obtained=80,
    )

    result2 = Result(
        school_id=student.school_id,
        student_id=student.id,
        exam_id=exam2.id,
        marks_obtained=60,
    )

    db.session.add_all([result1, result2])
    db.session.commit()

    return [result1, result2]


# ----------------------------------------------------------------------
# GET /admin/students/<student_id>/grade
# ----------------------------------------------------------------------

def test_get_student_grade_success(
    client,
    admin_headers,
    student,
    results_for_student,
):
    response = client.get(
        f"/admin/students/{student.id}/grade",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["student_id"] == student.id

    assert data["grade"]["total"] == 140
    assert data["grade"]["average"] == pytest.approx(70.0)
    assert data["grade"]["grade"] == "A"
    assert data["grade"]["remark"] == "Excellent"


def test_get_student_grade_no_results_404(
    client,
    admin_headers,
    student,
):
    response = client.get(
        f"/admin/students/{student.id}/grade",
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_get_student_grade_requires_admin_role(
    client,
    student,
):
    response = client.get(
        f"/admin/students/{student.id}/grade"
    )

    assert response.status_code in (401, 403)