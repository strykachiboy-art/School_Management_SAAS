import pytest
from datetime import time
from school_app.models.classroom import Classroom
from school_app.models.subject import Subject
from school_app.models.teacher import Teacher
from school_app.models.timetable import Timetable
from school_app.models.term import Term
from school_app.modules.admin_reports.services.admin_report_teachers_service import get_admin_report_teachers
from school_app.enums.day_of_week import DayOfWeek 

def test_get_admin_report_teachers_basic_and_filters(app, db_session):
    """Test teacher report generation with filters (gender, active status, etc.)."""
    with app.app_context():
        # 1. Setup test data
        subject = Subject(id=1, name="Mathematics", code="MATH101")
        classroom = Classroom(id=1, name="Grade 10A", capacity=30)
        term = Term(id=1, name="Term 1")
        
        teacher1 = Teacher(
            id=1,
            user_id=101,
            full_name="Alice Smith",
            email="alice@school.com",
            gender="Female",
            is_active=True
        )
        teacher2 = Teacher(
            id=2,
            user_id=102,
            full_name="Bob Jones",
            email="bob@school.com",
            gender="Male",
            is_active=False
        )

        # Associate relationships
        teacher1.subjects.append(subject)
        teacher1.classrooms.append(classroom)

        db_session.add_all([subject, classroom, teacher1, teacher2])
        db_session.commit()

        slot1 = Timetable(
            id=1, 
            teacher_id=1, 
            term_id =1,
            day_of_week=DayOfWeek.MONDAY,
            start_time=time(8, 0), 
            end_time=time(9, 0), 
            classroom_id=1, 
            subject_id=1
        )
        slot2 = Timetable(
            id=2, 
            teacher_id=1, 
            term_id =1,
            day_of_week=DayOfWeek.THURSDAY,
            start_time=time(8, 0), 
            end_time=time(9, 0), 
            classroom_id=1, 
            subject_id=1
        )
        db_session.add_all([slot1, slot2])
        db_session.commit()

        report = get_admin_report_teachers()
        
        assert report["total_teachers"] == 2
        assert report["active_count"] == 1
        assert report["inactive_count"] == 1
        assert report["by_gender"] == {"Female": 1, "Male": 1}
        
        teachers_list = report["teachers"]
       
        assert teachers_list[0]["full_name"] == "Alice Smith"
        assert teachers_list[0]["subjects"] == ["Mathematics"]
        assert teachers_list[0]["homeroom_classrooms"] == ["Grade 10A"]
        assert teachers_list[0]["weekly_timetable_slots"] == 2

        # 3. Test filtering by gender
        female_report = get_admin_report_teachers(gender="Female")
        assert female_report["total_teachers"] == 1
        assert female_report["teachers"][0]["full_name"] == "Alice Smith"

        # 4. Test filtering by active status
        active_report = get_admin_report_teachers(is_active=False)
        assert active_report["total_teachers"] == 1
        assert active_report["teachers"][0]["full_name"] == "Bob Jones"

        # 5. Test filtering by subject_id
        subject_report = get_admin_report_teachers(subject_id=1)
        assert subject_report["total_teachers"] == 1
        assert subject_report["teachers"][0]["teacher_id"] == 1

        # 6. Test filtering by classroom_id
        classroom_report = get_admin_report_teachers(classroom_id=1)
        assert classroom_report["total_teachers"] == 1
        assert classroom_report["teachers"][0]["teacher_id"] == 1