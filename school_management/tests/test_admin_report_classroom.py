from unittest.mock import patch
import pytest
from school_app.models.classroom import Classroom
from school_app.models.teacher import Teacher
from school_app.modules.admin_reports.services.admin_report_classrooms_service import get_admin_report_classrooms

@pytest.fixture
def mock_services():
    """Fixture to mock out dependent services so we can isolate classroom report logic."""
    with patch("school_app.modules.admin_reports.services.admin_report_classrooms_service.get_admin_report_academic") as mock_academic, \
         patch("school_app.modules.admin_reports.services.admin_report_classrooms_service.get_admin_report_attendance") as mock_attendance:
        
        mock_academic.return_value = {
            "classrooms": [
                {"classroom_id": 1, "average": 85.5, "pass_rate": 90.0}
            ]
        }
        mock_attendance.return_value = {
            "by_classroom": [
                {"classroom_id": 1, "attendance_rate": 95.2}
            ]
        }
        yield mock_academic, mock_attendance

def test_get_admin_report_classrooms(app, db_session, mock_services):
    """Test generating the classroom report with valid data."""
    with app.app_context():
        # Added user_id=1 to satisfy the NOT NULL constraint on the teachers table
        teacher = Teacher(id=1, user_id=1, full_name="Jane Doe")
        db_session.add(teacher)
        
        classroom = Classroom(
            id=1,
            name="Math 101",
            capacity=30,
            teacher_id=1
        )
        db_session.add(classroom)
        db_session.commit()

        report = get_admin_report_classrooms(session_id=1, term_id=1)

        assert len(report) == 1
        res = report[0]
        
        assert res["classroom_id"] == 1
        assert res["classroom_name"] == "Math 101"
        assert res["capacity"] == 30
        assert res["homeroom_teacher_id"] == 1   
        assert res["homeroom_teacher_name"] == "Jane Doe"  
        assert res["academic_average"] == 85.5
        assert res["academic_pass_rate"] == 90.0
        assert res["attendance_rate"] == 95.2
        assert res["capacity_utilization"] == 0.0