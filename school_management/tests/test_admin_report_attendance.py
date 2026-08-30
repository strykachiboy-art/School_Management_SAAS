import pytest
from datetime import date
from school_app.modules.admin_reports.services.admin_report_attendance_service import get_admin_report_attendance
from school_app.enums.attendance import AttendanceStatus

def test_get_admin_report_attendance_empty(app, db):
    with app.app_context():
        report = get_admin_report_attendance(session_id=9999)
        
        assert report["total_records"] == 0
        assert report["attendance_rate"] is None
        assert report["by_classroom"] == []
        assert report["by_student"] == []
        assert report["trend"] == []
        assert all(count == 0 for count in report["by_status"].values())

def test_get_admin_report_attendance_with_data(app, db, student, term, sample_present_attendance):
    with app.app_context():
        sample_present_attendance.term_id = term.id
        sample_present_attendance.student_id = student.id
        db.session.commit()

        report = get_admin_report_attendance(term_id=term.id)

        assert report["total_records"] >= 1
        assert report["attendance_rate"] == 100.0
        assert report["by_status"]["present"] >= 1
        assert len(report["by_classroom"]) >= 1
        assert len(report["by_student"]) >= 1
        assert len(report["trend"]) >= 1

