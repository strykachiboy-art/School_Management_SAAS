import pytest
from school_app.modules.admin_reports.services.admin_report_academic_service import get_admin_report_academic

def test_get_admin_report_academic_empty(app, db):
    with app.app_context():
        report = get_admin_report_academic(session_id=9999)
        
        assert report["overall_average"] is None
        assert report["pass_rate"] is None
        assert report["fail_rate"] is None
        assert report["total_results"] == 0
        assert report["subjects"] == []
        assert report["classrooms"] == []
        assert report["exams"] == []
        assert report["top_students"] == []
        assert report["lowest_students"] == []

def test_get_admin_report_academic_with_data(app, db, classroom, academic_session, term, subject, student, exam, result):
    with app.app_context():
        result.marks_obtained = 85.0
        db.session.commit()

        report = get_admin_report_academic(session_id=exam.session_id)

        assert report["total_results"] >= 1
        assert report["overall_average"] == 85.5
        assert report["pass_rate"] == 100.0
        assert report["fail_rate"] == 0.0
        assert len(report["subjects"]) >= 1
        assert len(report["classrooms"]) >= 1
        assert len(report["exams"]) >= 1
        assert len(report["top_students"]) >= 1

