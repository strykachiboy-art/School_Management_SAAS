from datetime import date, datetime, time, timezone

from school_app.extensions import db
from school_app.models.school import School
from school_app.models.user import User
from school_app.models.teacher import Teacher
from school_app.models.classroom import Classroom
from school_app.models.subject import Subject
from school_app.models.timetable import Timetable
from school_app.models.term import Term
from school_app.models.academic_session import AcademicSession
from school_app.models.association import teacher_subjects
from school_app.enums.day_of_week import DayOfWeek

from school_app.modules.admin_reports.services.admin_report_teachers_service import (
    get_admin_report_teachers,
)


def test_get_admin_report_teachers_basic_and_filters(app, db_session):
    """Test teacher report generation with filters."""

    with app.app_context():

        # ---------------------------------------------------------
        # 1. School
        # ---------------------------------------------------------
        school = School(
            id=1,
            name="Test School",
            slug="test-school",
            timezone="UTC",
            currency="USD",
            locale="en",
            is_active=True,
            onboarding_completed=True,
        )

        db_session.add(school)
        db_session.flush()

        # ---------------------------------------------------------
        # 2. Users
        #
        # Teacher.user_id is a required foreign key to users.id.
        # ---------------------------------------------------------
        user1 = User(
            id=101,
            username="alice",
            email="alice@school.com",
            school_id=school.id,
        )

        user2 = User(
            id=102,
            username="bob",
            email="bob@school.com",
            school_id=school.id,
        )

        db_session.add_all([user1, user2])
        db_session.flush()

        # ---------------------------------------------------------
        # 3. Academic Session
        #
        # AcademicSession requires:
        # school_id, name, start_date, end_date.
        # ---------------------------------------------------------
        academic_session = AcademicSession(
            id=1,
            school_id=school.id,
            name="2026/2027",
            start_date=datetime(2026, 9, 1, tzinfo=timezone.utc),
            end_date=datetime(2027, 7, 31, tzinfo=timezone.utc),
            is_active=True,
        )

        db_session.add(academic_session)
        db_session.flush()

        # ---------------------------------------------------------
        # 4. Subject
        # ---------------------------------------------------------
        subject = Subject(
            id=1,
            school_id=school.id,
            name="Mathematics",
            code="MATH101",
            description="Mathematics",
        )

        # ---------------------------------------------------------
        # 5. Teacher
        # ---------------------------------------------------------
        teacher1 = Teacher(
            id=1,
            school_id=school.id,
            user_id=user1.id,
            full_name="Alice Smith",
            email="alice@school.com",
            phone="08000000001",
            gender="Female",
            is_active=True,
        )

        teacher2 = Teacher(
            id=2,
            school_id=school.id,
            user_id=user2.id,
            full_name="Bob Jones",
            email="bob@school.com",
            phone="08000000002",
            gender="Male",
            is_active=False,
        )

        # ---------------------------------------------------------
        # 6. Classroom
        #
        # Classroom.teacher_id is the teacher/classroom relationship.
        # It is NOT a many-to-many association table.
        # ---------------------------------------------------------
        classroom = Classroom(
            id=1,
            school_id=school.id,
            name="Grade 10A",
            capacity=30,
            teacher_id=teacher1.id,
        )

        # ---------------------------------------------------------
        # 7. Term
        # ---------------------------------------------------------
        term = Term(
            id=1,
            school_id=school.id,
            name="Term 1",
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 18),
            is_current=True,
            academic_session_id=academic_session.id,
        )

        # ---------------------------------------------------------
        # 8. Add base records
        # ---------------------------------------------------------
        db_session.add_all([
            subject,
            teacher1,
            teacher2,
            classroom,
            term,
        ])

        db_session.flush()

        # ---------------------------------------------------------
        # 9. Teacher ↔ Subject association
        #
        # IMPORTANT:
        # teacher_subject has a required school_id column.
        #
        # Therefore we explicitly insert the association row
        # instead of using:
        #
        #     teacher1.subjects.append(subject)
        #
        # because SQLAlchemy's plain secondary table relationship
        # does not know how to populate school_id automatically.
        # ---------------------------------------------------------
        db_session.execute(
            teacher_subjects.insert().values(
                school_id=school.id,
                teacher_id=teacher1.id,
                subject_id=subject.id,
            )
        )

        db_session.commit()

        # ---------------------------------------------------------
        # 10. Timetable slots
        #
        # Timetable.school_id is also NOT NULL.
        # ---------------------------------------------------------
        slot1 = Timetable(
            id=1,
            school_id=school.id,
            teacher_id=teacher1.id,
            term_id=term.id,
            classroom_id=classroom.id,
            subject_id=subject.id,
            day_of_week=DayOfWeek.MONDAY,
            start_time=time(8, 0),
            end_time=time(9, 0),
        )

        slot2 = Timetable(
            id=2,
            school_id=school.id,
            teacher_id=teacher1.id,
            term_id=term.id,
            classroom_id=classroom.id,
            subject_id=subject.id,
            day_of_week=DayOfWeek.THURSDAY,
            start_time=time(8, 0),
            end_time=time(9, 0),
        )

        db_session.add_all([slot1, slot2])
        db_session.commit()

        # ---------------------------------------------------------
        # 11. Basic report
        # ---------------------------------------------------------
        report = get_admin_report_teachers()

        assert report["total_teachers"] == 2
        assert report["active_count"] == 1
        assert report["inactive_count"] == 1

        assert report["by_gender"] == {
            "Female": 1,
            "Male": 1,
        }

        teachers_list = report["teachers"]

        # ---------------------------------------------------------
        # Alice
        # ---------------------------------------------------------
        alice = teachers_list[0]

        assert alice["teacher_id"] == 1
        assert alice["full_name"] == "Alice Smith"
        assert alice["email"] == "alice@school.com"
        assert alice["phone"] == "08000000001"
        assert alice["gender"] == "Female"
        assert alice["is_active"] is True

        assert alice["subjects"] == ["Mathematics"]
        assert alice["homeroom_classrooms"] == ["Grade 10A"]
        assert alice["weekly_timetable_slots"] == 2

        # ---------------------------------------------------------
        # Bob
        # ---------------------------------------------------------
        bob = teachers_list[1]

        assert bob["teacher_id"] == 2
        assert bob["full_name"] == "Bob Jones"
        assert bob["email"] == "bob@school.com"
        assert bob["phone"] == "08000000002"
        assert bob["gender"] == "Male"
        assert bob["is_active"] is False

        assert bob["subjects"] == []
        assert bob["homeroom_classrooms"] == []
        assert bob["weekly_timetable_slots"] == 0

        # ---------------------------------------------------------
        # 12. Filter by gender
        # ---------------------------------------------------------
        female_report = get_admin_report_teachers(
            gender="Female"
        )

        assert female_report["total_teachers"] == 1
        assert female_report["active_count"] == 1
        assert female_report["inactive_count"] == 0

        assert female_report["teachers"][0]["teacher_id"] == 1
        assert female_report["teachers"][0]["full_name"] == "Alice Smith"

        # ---------------------------------------------------------
        # 13. Filter by active status
        # ---------------------------------------------------------
        inactive_report = get_admin_report_teachers(
            is_active=False
        )

        assert inactive_report["total_teachers"] == 1
        assert inactive_report["active_count"] == 0
        assert inactive_report["inactive_count"] == 1

        assert inactive_report["teachers"][0]["teacher_id"] == 2
        assert inactive_report["teachers"][0]["full_name"] == "Bob Jones"

        # ---------------------------------------------------------
        # 14. Filter by subject
        # ---------------------------------------------------------
        subject_report = get_admin_report_teachers(
            subject_id=subject.id
        )

        assert subject_report["total_teachers"] == 1
        assert subject_report["teachers"][0]["teacher_id"] == 1
        assert subject_report["teachers"][0]["full_name"] == "Alice Smith"

        # ---------------------------------------------------------
        # 15. Filter by classroom
        # ---------------------------------------------------------
        classroom_report = get_admin_report_teachers(
            classroom_id=classroom.id
        )

        assert classroom_report["total_teachers"] == 1
        assert classroom_report["teachers"][0]["teacher_id"] == 1
        assert classroom_report["teachers"][0]["full_name"] == "Alice Smith"