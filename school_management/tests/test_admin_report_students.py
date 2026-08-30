from unittest.mock import patch
import pytest
from datetime import date, time
from school_app.models.student import Student
from school_app.models.classroom import Classroom
from school_app.models.academic_session import AcademicSession
from school_app.models.term import Term
from school_app.models.result import Result
from school_app.models.exam import Exam
from school_app.models.subject import Subject
from school_app.models.attendance import Attendance
from school_app.enums.attendance import AttendanceStatus
from school_app.models.school_fees import Invoice
from school_app.enums.school_fees import InvoiceStatus
from school_app.modules.admin_reports.services.admin_report_students_service import get_admin_report_students


@pytest.fixture(autouse=True)
def mock_grade_service():
    """Mock the grade calculation service to return a consistent grade in tests."""
    with patch("school_app.modules.admin_reports.services.admin_report_students_service.calculate_grade", return_value="A") as mock_grade:
        yield mock_grade


def test_get_admin_report_students_comprehensive(app, db_session):
    """Test student report generation, including filters, aggregations, and individual student metrics."""
    with app.app_context():
        # 1. Setup Master Data with required start and end dates
        session = AcademicSession(
            id=1, 
            name="2025/2026", 
            start_date=date(2025, 9, 1), 
            end_date=date(2026, 7, 31)
        )
        term = Term(
            id=1, 
            name="First Term",
            start_date=date(2025, 9, 1), 
            end_date=date(2025, 12, 1),
            academic_session_id=session.id
        )
        
        classroom = Classroom(id=1, name="Grade 10A", capacity=30)
        subject = Subject(id=1, name="Mathematics", code="MATH101")

        db_session.add_all([session, term, classroom, subject])
        db_session.commit()

        # 2. Setup Students
        student1 = Student(
            id=1,
            user_id=201,
            full_name="Alice Smith",
            admission_number="ADM001",
            gender="Female",
            is_active=True,
            classroom_id=1,
            current_session_id=1,
            current_term_id=1
        )
        student2 = Student(
            id=2,
            user_id=202,
            full_name="Bob Jones",
            admission_number="ADM002",
            gender="Male",
            is_active=False,
            classroom_id=1,
            current_session_id=1,
            current_term_id=1
        )

        db_session.add_all([student1, student2])
        db_session.commit()
        
        exam1 = Exam(
            id=1,
            title="Math Quiz", 
            session_id=1,
            subject_id=1,  
            classroom_id=1,
            exam_date=date(2025, 10, 15),
            start_time=time(9, 0),
            duration_minutes=60,
            total_marks=100
        )
        result1 = Result(id=1, exam_id=1, student_id=1, marks_obtained=85.0)
        
        attendance1 = Attendance(
            id=1, 
            student_id=1, 
            term_id=1, 
            date=date(2025, 9, 10), 
            status=AttendanceStatus.PRESENT
        )
        attendance2 = Attendance(
            id=2, 
            student_id=1, 
            term_id=1, 
            date=date(2025, 9, 11), 
            status=AttendanceStatus.ABSENT
        )

        invoice1 = Invoice(
            id=1, 
            student_id=1, 
            session_id=1, 
            term_id=1, 
            total_amount=1000.0,
            status=InvoiceStatus.PAID
        )

        db_session.add_all([exam1, result1, attendance1, attendance2, invoice1])
        db_session.commit()

        # --- Test 1: Basic Report & Aggregations ---
        report = get_admin_report_students()

        assert report["total_students"] == 2
        assert report["active_count"] == 1
        assert report["inactive_count"] == 1
        assert report["by_gender"] == {"Female": 1, "Male": 1}
        assert len(report["by_classroom"]) == 1
        assert report["by_classroom"][0]["classroom_name"] == "Grade 10A"
        assert report["by_classroom"][0]["count"] == 2

        # Check per-student rows (sorted by full_name)
        students_list = report["students"]
        assert len(students_list) == 2

        alice_row = students_list[0]
        assert alice_row["full_name"] == "Alice Smith"
        assert alice_row["academic_average"] == 85.0
        assert alice_row["grade"] == "A"
        assert alice_row["attendance_rate"] == 50.0
        assert alice_row["fees_status"] == "paid_up"

        bob_row = students_list[1]
        assert bob_row["full_name"] == "Bob Jones"
        assert bob_row["fees_status"] == "no_fees_on_record"

        # --- Test 2: Filter by Classroom ---
        classroom_filtered = get_admin_report_students(classroom_id=1)
        assert classroom_filtered["total_students"] == 2

        # --- Test 3: Filter by Gender ---
        female_filtered = get_admin_report_students(gender="Female")
        assert female_filtered["total_students"] == 1
        assert female_filtered["students"][0]["full_name"] == "Alice Smith"

        # --- Test 4: Filter by Active Status ---
        inactive_filtered = get_admin_report_students(is_active=False)
        assert inactive_filtered["total_students"] == 1
        assert inactive_filtered["students"][0]["full_name"] == "Bob Jones"

        # --- Test 5: Filter by Session & Term ---
        session_term_filtered = get_admin_report_students(session_id=1, term_id=1)
        assert session_term_filtered["total_students"] == 2