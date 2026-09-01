from school_app.models.student import Student
from school_app.models.teacher import Teacher
from school_app.models.subject import Subject
from school_app.models.classroom import Classroom


def test_get_admin_report_counts(
    client,
    admin_headers,
    teacher,
    student,
    subject,
    classroom,
):
    """Verify that the overview report returns the correct counts."""

    response = client.get(
        "/admin/reports/overview",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    students_total = data.get("students", {}).get("total")
    teachers_total = data.get("teachers", {}).get("total")
    subjects_total = data.get("subjects", {}).get("total")
    classrooms_total = data.get("classrooms", {}).get("total")

    if students_total is None:
        students_total = data.get("total_students")

    if teachers_total is None:
        teachers_total = data.get("total_teachers")

    if subjects_total is None:
        subjects_total = data.get("total_subjects")

    if classrooms_total is None:
        classrooms_total = data.get("total_classrooms")

    assert students_total == 1
    assert teachers_total == 1
    assert subjects_total == 1
    assert classrooms_total == 1


def test_get_admin_report_empty(
    client,
    admin_headers,
):
    """Verify that the overview report is empty when no records exist."""

    response = client.get(
        "/admin/reports/overview",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    students_total = data.get("students", {}).get("total")
    teachers_total = data.get("teachers", {}).get("total")
    subjects_total = data.get("subjects", {}).get("total")
    classrooms_total = data.get("classrooms", {}).get("total")

    if students_total is None:
        students_total = data.get("total_students")

    if teachers_total is None:
        teachers_total = data.get("total_teachers")

    if subjects_total is None:
        subjects_total = data.get("total_subjects")

    if classrooms_total is None:
        classrooms_total = data.get("total_classrooms")

    assert students_total == 0
    assert teachers_total == 0
    assert subjects_total == 0
    assert classrooms_total == 0


def test_get_admin_report_requires_admin_role(
    client,
    teacher_headers,
):
    """Verify that teachers cannot access admin reports."""

    response = client.get(
        "/admin/reports/overview",
        headers=teacher_headers,
    )

    assert response.status_code == 403


def test_get_admin_report_requires_auth(client):
    """Verify that unauthenticated users cannot access admin reports."""

    response = client.get(
        "/admin/reports/overview",
    )

    assert response.status_code in (401, 403)
