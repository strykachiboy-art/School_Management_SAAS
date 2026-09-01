import pytest
from unittest.mock import patch

from school_app.modules.admin_reports.services.admin_report_classrooms_service import (
    get_admin_report_classrooms,
)


@pytest.fixture
def mock_services():
    with patch(
        "school_app.modules.admin_reports.services.admin_report_classrooms_service."
        "get_admin_report_academic"
    ) as mock_academic, patch(
        "school_app.modules.admin_reports.services.admin_report_classrooms_service."
        "get_admin_report_attendance"
    ) as mock_attendance:

        mock_academic.return_value = {
            "classrooms": [
                {
                    "classroom_id": 1,
                    "average": 85.5,
                    "pass_rate": 90.0,
                }
            ]
        }

        mock_attendance.return_value = {
            "by_classroom": [
                {
                    "classroom_id": 1,
                    "attendance_rate": 95.2,
                }
            ]
        }

        yield mock_academic, mock_attendance


def test_get_admin_report_classrooms(
    app,
    db_session,
    school,
    teacher,
    classroom,
    mock_services,
):
    """
    Test classroom report generation using the project's standard
    school, teacher, and classroom fixtures.
    """

    with app.app_context():
        # ---------------------------------------------------------
        # Attach the classroom to the existing teacher.
        # ---------------------------------------------------------
        classroom_obj = db_session.merge(classroom)
        teacher_obj = db_session.merge(teacher)

        classroom_obj.teacher_id = teacher_obj.id

        db_session.commit()

        # ---------------------------------------------------------
        # Generate report.
        # ---------------------------------------------------------
        report = get_admin_report_classrooms(
            session_id=1,
            term_id=1,
        )

        # ---------------------------------------------------------
        # Assertions.
        # ---------------------------------------------------------
        assert isinstance(report, list)
        assert len(report) == 1

        result = report[0]

        assert result["classroom_id"] == classroom_obj.id
        assert result["classroom_name"] == classroom_obj.name
        assert result["capacity"] == classroom_obj.capacity

        assert result["homeroom_teacher_id"] == teacher_obj.id
        assert result["homeroom_teacher_name"] == teacher_obj.full_name

        assert result["academic_average"] == 85.5
        assert result["academic_pass_rate"] == 90.0
        assert result["attendance_rate"] == 95.2

        # No students were attached to the classroom.
        assert result["capacity_utilization"] == 0.0
