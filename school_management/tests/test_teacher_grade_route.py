import pytest
from flask_jwt_extended import create_access_token

from school_app.extensions import db
from school_app.models.result import Result

JSON_HEADERS = {"Accept": "application/json"}


# ======================================================================
# Get Student Grade (Teacher Route) Tests
# ======================================================================

def test_get_student_grade_success(
    client,
    teacher_headers,
    student_in_teacher_classroom,
    exam,
):
    """Teacher can view the grade of a student in their own classroom."""
    student = student_in_teacher_classroom

    # Result.school_id is required, so use the student's school.
    result = Result(
        school_id=student.school_id,
        student_id=student.id,
        exam_id=exam.id,
        marks_obtained=75,
    )

    db.session.add(result)
    db.session.commit()

    response = client.get(
        f"/teacher/students/{student.id}/grade",
        headers=teacher_headers,
    )

    assert response.status_code == 200

    data = response.get_json()
    assert data["student_id"] == student.id
    assert data["grade"]["total"] == 75
    assert data["grade"]["average"] == pytest.approx(75.0)
    assert data["grade"]["grade"] == "A"


def test_get_student_grade_student_not_found(client, teacher_headers):
    response = client.get(
        "/teacher/students/9999/grade",
        headers=teacher_headers,
    )

    assert response.status_code == 404


def test_get_student_grade_student_no_classroom(
    client,
    teacher_headers,
    student,
):
    """Student exists but has no classroom_id set -> ValueError -> 404."""
    response = client.get(
        f"/teacher/students/{student.id}/grade",
        headers=teacher_headers,
    )

    assert response.status_code == 404


def test_get_student_grade_wrong_teacher(
    client,
    teacher_headers,
    student_in_teacher_classroom,
    teacher2,
    classroom,
):
    """A different teacher tries to view a student belonging to another teacher's classroom."""
    student = student_in_teacher_classroom

    with client.application.app_context():
        token = create_access_token(
            identity=str(teacher2.user_id),
            additional_claims={"role": "teacher"},
        )

    other_teacher_headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    response = client.get(
        f"/teacher/students/{student.id}/grade",
        headers=other_teacher_headers,
    )

    assert response.status_code == 404


def test_get_student_grade_requires_teacher_role(
    client,
    admin_headers,
    student_in_teacher_classroom,
):
    """An admin token should not satisfy the teacher-only route."""
    student = student_in_teacher_classroom

    response = client.get(
        f"/teacher/students/{student.id}/grade",
        headers=admin_headers,
    )

    assert response.status_code == 403


def test_get_student_grade_requires_auth(
    client,
    student_in_teacher_classroom,
):
    student = student_in_teacher_classroom

    response = client.get(
        f"/teacher/students/{student.id}/grade"
    )
    assert response.status_code in (401, 403)