import pytest
from datetime import date
from decimal import Decimal
from school_app.models.attendance import Attendance
from school_app.enums.attendance import AttendanceStatus
from school_app.models.school_fees import Invoice
from school_app.models.academic_session import AcademicSession
from school_app.models.term import Term


# --- Authentication Guard Tests ---

@pytest.mark.parametrize("endpoint", [
    "/admin/reports/overview",
    "/admin/reports/academic",
    "/admin/reports/attendance",
    "/admin/reports/classrooms",
    "/admin/reports/students",
    "/admin/reports/teachers",
])
def test_admin_reports_require_auth(client, endpoint):
    """Ensure all report endpoints return 401 or 403 when unauthenticated."""
    response = client.get(endpoint)
    assert response.status_code in (401, 403)


# --- Endpoint Structure & Response Tests ---

def test_get_admin_report_overview_endpoint(client, admin_headers, student, db_session):
    session = AcademicSession(
        name="2025/2026", start_date=date(2025, 9, 1), end_date=date(2026, 7, 1), is_active=True
    )
    db_session.add(session)
    db_session.flush()
    
    term = Term(
        name="Term 1", academic_session_id=session.id,
        start_date=date(2025, 9, 1), end_date=date(2025, 12, 1), is_current=True,
    )
    db_session.add(term)
    db_session.flush()

    db_session.add_all([
        Attendance(student_id=student.id, term_id=term.id, date=date(2026, 1, 5), status=AttendanceStatus.PRESENT),
        Attendance(student_id=student.id, term_id=term.id, date=date(2026, 1, 6), status=AttendanceStatus.ABSENT),
    ])
    db_session.add(Invoice(
        student_id=student.id, session_id=session.id, term_id=term.id,
        total_amount=Decimal("1000.00"), discount_amount=Decimal("100.00"),
        waived_amount=Decimal("0.00"), amount_paid=Decimal("300.00"),
    ))
    db_session.commit()

    response = client.get("/admin/reports/overview", headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert "students" in data
    assert data["students"]["total"] >= 1


def test_get_admin_report_academic_endpoint(client, admin_headers):
    response = client.get("/admin/reports/academic?session_id=1&classroom_id=1", headers=admin_headers)
    assert response.status_code == 200
    assert isinstance(response.get_json(), (dict, list))


def test_get_admin_report_attendance_endpoint(client, admin_headers):
    response = client.get(
        "/admin/reports/attendance?start_date=2026-01-01&end_date=2026-01-31", 
        headers=admin_headers
    )
    assert response.status_code == 200
    assert isinstance(response.get_json(), (dict, list))


def test_get_admin_report_classrooms_endpoint(client, admin_headers):
    response = client.get("/admin/reports/classrooms?session_id=1", headers=admin_headers)
    assert response.status_code == 200
    assert isinstance(response.get_json(), (dict, list))


def test_get_admin_report_students_endpoint(client, admin_headers):
    response = client.get(
        "/admin/reports/students?gender=Female&is_active=true&start_date=2025-09-01", 
        headers=admin_headers
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "total_students" in data or isinstance(data, dict)


def test_get_admin_report_teachers_endpoint(client, admin_headers):
    response = client.get("/admin/reports/teachers?gender=Male&is_active=false", headers=admin_headers)
    assert response.status_code == 200
    assert isinstance(response.get_json(), (dict, list))