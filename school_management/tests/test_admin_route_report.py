from school_app.extensions import db
from school_app.models.student import Student
from school_app.models.teacher import Teacher
from school_app.models.subject import Subject
from school_app.models.classroom import Classroom

JSON_HEADERS = {"Accept": "application/json"}

def test_get_admin_report_counts(client, admin_headers, teacher, student, subject, classroom):
    response = client.get("/admin/reports/overview", headers=admin_headers)
    assert response.status_code == 200

    data = response.get_json()
    assert data.get("total_students", data.get("students", {}).get("total")) == 1
    assert data.get("total_teachers", data.get("teachers", {}).get("total")) == 1
    assert data.get("total_subjects", data.get("subjects", {}).get("total")) == 1
    assert data.get("total_classrooms", data.get("classrooms", {}).get("total")) == 1


def test_get_admin_report_empty(client, admin_headers):
    """No teacher/student/subject/classroom fixtures used -> all counts should be 0."""
    response = client.get("/admin/reports/overview", headers=admin_headers)
    assert response.status_code == 200

    data = response.get_json()
    assert data.get("total_students", data.get("students", {}).get("total")) == 0
    assert data.get("total_teachers", data.get("teachers", {}).get("total")) == 0
    assert data.get("total_subjects", data.get("subjects", {}).get("total")) == 0
    assert data.get("total_classrooms", data.get("classrooms", {}).get("total")) == 0


def test_get_admin_report_requires_admin_role(client, teacher_headers):
    response = client.get("/admin/reports/overview", headers=teacher_headers)
    assert response.status_code == 403


def test_get_admin_report_requires_auth(client):
    response = client.get("/admin/reports/overview")
    assert response.status_code in (401, 403)