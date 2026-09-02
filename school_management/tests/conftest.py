import uuid
from datetime import date, time
import secrets

import pytest
from sqlalchemy import UniqueConstraint, text
from flask_jwt_extended import create_access_token

from school_app import create_app
from school_app.enums.attendance import AttendanceStatus
from school_app.enums.day_of_week import DayOfWeek
from school_app.enums.enrollment import EnrollmentStatus
from school_app.enums.notification import NotificationType
from school_app.enums.reportcard import ReportCardStatus
from school_app.extensions import db as _db, limiter, redis_client

from school_app.models.academic_session import AcademicSession
from school_app.models.academic_stage import AcademicStage
from school_app.models.attendance import Attendance
from school_app.models.classroom import Classroom
from school_app.models.exam import Exam
from school_app.models.notification import Notification
from school_app.models.parent_guardian import ParentGuardian
from school_app.models.reportcard import ReportCard
from school_app.models.result import Result
from school_app.models.school import School
from school_app.models.student import Student
from school_app.models.student_enrollment import StudentEnrollment
from school_app.models.subject import Subject
from school_app.models.teacher import Teacher
from school_app.models.term import Term
from school_app.models.timetable import Timetable
from school_app.models.user import User
from school_app.models.onboarding_progress import OnboardingProgress


# ======================================================================
# 1. APP / DATABASE FIXTURES
# ======================================================================

@pytest.fixture(scope="function")
def app():
    """
    Create an isolated Flask application and in-memory SQLite database
    for every test.

    StudentEnrollment has an intentional partial unique index:

        UNIQUE(school_id, student_id, academic_session_id)
        WHERE status = 'active'

    This allows historical enrollment records while preventing two
    simultaneous ACTIVE enrollments for the same student/session/school.
    """

    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JWT_SECRET_KEY": (
            "test-secret-key-that-is-at-least-32-bytes-long"
        ),
        "RATELIMIT_ENABLED": True,
        "RATELIMIT_STORAGE_URI": "memory://",
        "WTF_CSRF_ENABLED": False,
        "ADMIN_ACCESS_ENABLED": True,
    }

    app = create_app(config=test_config)

    with app.app_context():

        enrollment_table = StudentEnrollment.__table__

        enrollment_columns = {
            "school_id",
            "student_id",
            "academic_session_id",
        }

        removed_constraints = []
        removed_indexes = []

        # --------------------------------------------------------------
        # Remove legacy unconditional UNIQUE constraints.
        #
        # We only remove constraints covering exactly:
        #
        #   school_id
        #   student_id
        #   academic_session_id
        #
        # The current intended uniqueness rule is implemented by the
        # partial index uq_active_student_enrollment.
        # --------------------------------------------------------------

        for constraint in list(enrollment_table.constraints):

            if not isinstance(constraint, UniqueConstraint):
                continue

            constraint_columns = {
                column.name
                for column in constraint.columns
            }

            if constraint_columns == enrollment_columns:
                enrollment_table.constraints.remove(constraint)
                removed_constraints.append(constraint)

        # --------------------------------------------------------------
        # Remove legacy unconditional UNIQUE indexes.
        #
        # NEVER remove:
        #
        #   uq_active_student_enrollment
        #
        # because this is the intended partial unique index.
        # --------------------------------------------------------------

        for index in list(enrollment_table.indexes):

            if not index.unique:
                continue

            if index.name == "uq_active_student_enrollment":
                continue

            index_columns = {
                column.name
                for column in index.columns
            }

            if index_columns == enrollment_columns:
                enrollment_table.indexes.remove(index)
                removed_indexes.append(index)

        # --------------------------------------------------------------
        # Create all test tables after the metadata cleanup.
        # --------------------------------------------------------------

        _db.create_all()

        try:
            yield app

        finally:
            # ----------------------------------------------------------
            # Dispose of the current session first.
            # ----------------------------------------------------------

            _db.session.remove()

            # ----------------------------------------------------------
            # Drop all test tables.
            # ----------------------------------------------------------

            _db.drop_all()

            # ----------------------------------------------------------
            # Restore metadata exactly as it was before the fixture.
            #
            # This prevents test-specific metadata manipulation from
            # leaking into subsequent tests.
            # ----------------------------------------------------------

            for constraint in removed_constraints:

                if constraint not in enrollment_table.constraints:
                    enrollment_table.append_constraint(constraint)

            for index in removed_indexes:

                if index not in enrollment_table.indexes:
                    enrollment_table.append_constraint(index)


@pytest.fixture(scope="function")
def db(app):
    """Provides the SQLAlchemy db instance."""
    return _db


@pytest.fixture(scope="function")
def db_session(app, db):
    """Provides convenient access to db.session."""
    return db.session


# ======================================================================
# 2. SCHOOL FIXTURE
# ======================================================================

@pytest.fixture
def school(app):
    """Creates the default school used by most tenant-scoped tests."""

    with app.app_context():

        school = School(
            name="Test School",
            slug="test-school",
        )

        _db.session.add(school)
        _db.session.commit()

        _db.session.refresh(school)
        _db.session.expunge(school)

        return school


# ======================================================================
# 3. GLOBAL CLEANUP
# ======================================================================

@pytest.fixture(autouse=True)
def auto_clear_limiter(app):
    """Reset Flask-Limiter state after every test."""

    yield

    with app.app_context():

        if getattr(limiter, "_storage", None) is not None:

            try:
                limiter.reset()
            except Exception:
                pass


@pytest.fixture(autouse=True)
def auto_clear_redis(app):
    """
    Remove refresh-token whitelist entries after every test.

    Redis may not be running locally, so cleanup failures are ignored.
    """

    yield

    with app.app_context():

        try:
            keys = redis_client.keys("refresh_whitelist:*")

            if keys:
                redis_client.delete(*keys)

        except Exception:
            pass


# ======================================================================
# 4. HTTP CLIENTS
# ======================================================================

@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def json_client(client):
    """
    Test client wrapper that automatically sends
    Accept: application/json.
    """

    class JSONClient:

        def __init__(self, test_client):
            self.c = test_client
            self.headers = {
                "Accept": "application/json",
            }

        def _kwargs(self, kwargs):
            kwargs["headers"] = {
                **self.headers,
                **kwargs.get("headers", {}),
            }
            return kwargs

        def post(self, url, **kwargs):
            return self.c.post(
                url,
                **self._kwargs(kwargs),
            )

        def patch(self, url, **kwargs):
            return self.c.patch(
                url,
                **self._kwargs(kwargs),
            )

        def put(self, url, **kwargs):
            return self.c.put(
                url,
                **self._kwargs(kwargs),
            )

        def get(self, url, **kwargs):
            return self.c.get(
                url,
                **self._kwargs(kwargs),
            )

        def delete(self, url, **kwargs):
            return self.c.delete(
                url,
                **self._kwargs(kwargs),
            )

    return JSONClient(client)


@pytest.fixture
def admin_client(client, admin_headers):
    """
    Test client wrapper that automatically attaches admin auth.
    """

    class AdminClient:

        def __init__(self, test_client):
            self.c = test_client
            self.headers = admin_headers

        def _kwargs(self, kwargs):
            kwargs["headers"] = {
                **self.headers,
                **kwargs.get("headers", {}),
            }
            return kwargs

        def post(self, url, **kwargs):
            return self.c.post(
                url,
                **self._kwargs(kwargs),
            )

        def patch(self, url, **kwargs):
            return self.c.patch(
                url,
                **self._kwargs(kwargs),
            )

        def put(self, url, **kwargs):
            return self.c.put(
                url,
                **self._kwargs(kwargs),
            )

        def get(self, url, **kwargs):
            return self.c.get(
                url,
                **self._kwargs(kwargs),
            )

        def delete(self, url, **kwargs):
            return self.c.delete(
                url,
                **self._kwargs(kwargs),
            )

    return AdminClient(client)


# ======================================================================
# 5. ACADEMIC STAGE
# ======================================================================

@pytest.fixture
def admin_stage(app, school):
    """Creates a default AcademicStage for the test school."""

    with app.app_context():

        stage = AcademicStage(
            name=f"Stage {uuid.uuid4().hex[:6]}",
            display_order=1,
            school_id=school.id,
        )

        _db.session.add(stage)
        _db.session.commit()

        _db.session.refresh(stage)
        _db.session.expunge(stage)

        return stage


# ======================================================================
# 6. USER FACTORY
# ======================================================================

@pytest.fixture
def make_user(app, school):

    _UNSET = object()

    def _make(
        suffix="1",
        role="student",
        school_id=_UNSET,
    ):

        with app.app_context():

            if role == "platform_admin":
                resolved_school_id = None

            elif school_id is _UNSET:
                resolved_school_id = school.id

            else:
                resolved_school_id = school_id

            user = User(
                username=f"user_{suffix}",
                email=f"user_{suffix}@example.com",
                password="hashed-placeholder",
                role=role,
                school_id=resolved_school_id,
            )

            _db.session.add(user)
            _db.session.commit()

            _db.session.refresh(user)
            _db.session.expunge(user)

            return user

    return _make


# ======================================================================
# 7. USER ROLE FACTORIES
# ======================================================================

@pytest.fixture
def make_teacher(app, school):

    def _make(suffix="1"):

        with app.app_context():

            user = User(
                username=f"teacher_{suffix}",
                email=f"teacher_{suffix}@example.com",
                password="hashed-placeholder",
                role="teacher",
                school_id=school.id,
            )

            _db.session.add(user)
            _db.session.flush()

            teacher = Teacher(
                user_id=user.id,
                full_name=f"Teacher {suffix}",
                school_id=school.id,
            )

            _db.session.add(teacher)
            _db.session.commit()

            _db.session.refresh(teacher)
            _db.session.expunge(teacher)

            return teacher

    return _make


@pytest.fixture
def make_student(app, school):

    def _make(suffix="1"):

        with app.app_context():

            user = User(
                username=f"student_{suffix}",
                email=f"student_{suffix}@example.com",
                password="hashed-placeholder",
                role="student",
                school_id=school.id,
            )

            _db.session.add(user)
            _db.session.flush()

            student = Student(
                user_id=user.id,
                full_name=f"Student {suffix}",
                school_id=school.id,
            )

            _db.session.add(student)
            _db.session.commit()

            _db.session.refresh(student)
            _db.session.expunge(student)

            return student

    return _make


@pytest.fixture
def make_parent(app, school):

    def _make(suffix="1"):

        with app.app_context():

            user = User(
                username=f"parent_{suffix}",
                email=f"parent_{suffix}@example.com",
                password="hashed-placeholder",
                role="parent",
                school_id=school.id,
            )

            _db.session.add(user)
            _db.session.flush()

            parent = ParentGuardian(
                user_id=user.id,
                occupation=f"Profession {suffix}",
                email=f"parent_{suffix}@example.com",
                phone="08012345678",
                address="123 Test Street",
                school_id=school.id,
            )

            _db.session.add(parent)
            _db.session.commit()

            _db.session.refresh(parent)
            _db.session.expunge(parent)

            return parent

    return _make


# ======================================================================
# 8. MODEL FACTORIES
# ======================================================================

@pytest.fixture
def make_classroom(app, school):

    def _make(suffix="1"):

        with app.app_context():

            classroom = Classroom(
                name=f"Room {suffix}",
                capacity=30,
                school_id=school.id,
            )

            _db.session.add(classroom)
            _db.session.commit()

            _db.session.refresh(classroom)
            _db.session.expunge(classroom)

            return classroom

    return _make


@pytest.fixture
def make_notification(app):

    def _make(
        recipient_user_id,
        title="Test Notification",
        message="Test message",
        notification_type=NotificationType.GENERAL,
        is_read=False,
    ):

        with app.app_context():

            notification = Notification(
                recipient_id=recipient_user_id,
                title=title,
                message=message,
                notification_type=notification_type,
                is_read=is_read,
            )

            _db.session.add(notification)
            _db.session.commit()

            _db.session.refresh(notification)
            _db.session.expunge(notification)

            return notification

    return _make


@pytest.fixture
def make_exam(
    app,
    subject,
    classroom,
    academic_session,
    school,
    term,
):

    def _make(
        suffix="1",
        subject_obj=None,
        classroom_obj=None,
        session_obj=None,
        term_obj=None,
        exam_date_val=date(2026, 12, 1),
        start_time_val=time(9, 0),
        duration_minutes=90,
        total_marks=100,
    ):

        with app.app_context():

            subject_obj = subject_obj or subject
            classroom_obj = classroom_obj or classroom
            session_obj = session_obj or academic_session
            term_obj = term_obj or term

            exam = Exam(
                school_id=school.id,
                title=f"Exam {suffix}",
                description="Test description",
                subject_id=subject_obj.id,
                classroom_id=classroom_obj.id,
                session_id=session_obj.id,
                term_id=(
                    term_obj.id
                    if term_obj
                    else None
                ),
                exam_date=exam_date_val,
                start_time=start_time_val,
                duration_minutes=duration_minutes,
                total_marks=total_marks,
            )

            _db.session.add(exam)
            _db.session.commit()

            _db.session.refresh(exam)
            _db.session.expunge(exam)

            return exam

    return _make


@pytest.fixture
def make_result(app, student, exam, school):

    def _make(
        student_obj=None,
        exam_obj=None,
        marks=85.5,
    ):

        with app.app_context():

            student_obj = student_obj or student
            exam_obj = exam_obj or exam

            result = Result(
                school_id=school.id,
                student_id=student_obj.id,
                exam_id=exam_obj.id,
                marks_obtained=marks,
            )

            _db.session.add(result)
            _db.session.commit()

            _db.session.refresh(result)
            _db.session.expunge(result)

            return result

    return _make


@pytest.fixture
def make_timetable(
    app,
    term,
    classroom,
    subject,
    teacher,
    school,
):

    def _make(
        term_obj=None,
        classroom_obj=None,
        subject_obj=None,
        teacher_obj=None,
        school_id=None,
        day_of_week=DayOfWeek.MONDAY,
        start_time_val=time(8, 0),
        end_time_val=time(9, 0),
    ):

        with app.app_context():

            term_obj = term_obj or term
            classroom_obj = classroom_obj or classroom
            subject_obj = subject_obj or subject
            teacher_obj = teacher_obj or teacher

            timetable = Timetable(
                school_id=(
                    school.id
                    if school_id is None
                    else school_id
                ),
                term_id=term_obj.id,
                classroom_id=classroom_obj.id,
                subject_id=subject_obj.id,
                teacher_id=teacher_obj.id,
                day_of_week=day_of_week,
                start_time=start_time_val,
                end_time=end_time_val,
            )

            _db.session.add(timetable)
            _db.session.commit()

            _db.session.refresh(timetable)
            _db.session.expunge(timetable)

            return timetable

    return _make


@pytest.fixture
def make_attendance(app, student, term, school):

    def _make(
        student_obj=None,
        term_obj=None,
        date_val=date(2026, 9, 10),
        status=AttendanceStatus.PRESENT,
    ):

        with app.app_context():

            student_obj = student_obj or student
            term_obj = term_obj or term

            attendance = Attendance(
                student_id=student_obj.id,
                term_id=term_obj.id,
                date=date_val,
                status=status,
                school_id=school.id,
            )

            _db.session.add(attendance)
            _db.session.commit()

            _db.session.refresh(attendance)
            _db.session.expunge(attendance)

            return attendance

    return _make


# ======================================================================
# 9. STUDENT ENROLLMENT FACTORY
# ======================================================================

@pytest.fixture
def make_enrollment(
    app,
    student,
    classroom,
    academic_session,
    school,
):

    def _make(
        student_obj=None,
        classroom_obj=None,
        session_obj=None,
        status=EnrollmentStatus.ACTIVE,
        enrollment_date=None,
        withdrawal_date=None,
        enrollment_date_val=None,
        withdrawal_date_val=None,
        remarks=None,
        recorded_by=None,
        school_id=None,
    ):

        with app.app_context():

            student_obj = student_obj or student
            classroom_obj = classroom_obj or classroom
            session_obj = session_obj or academic_session

            # ----------------------------------------------------------
            # Backward-compatible aliases.
            # ----------------------------------------------------------

            if enrollment_date_val is not None:
                enrollment_date = enrollment_date_val

            if withdrawal_date_val is not None:
                withdrawal_date = withdrawal_date_val

            # ----------------------------------------------------------
            # IMPORTANT:
            #
            # Do not infer withdrawal_date from status.
            #
            # The current database uniqueness rule is based on:
            #
            #     status = 'active'
            #
            # rather than withdrawal_date IS NULL.
            #
            # Therefore historical statuses such as:
            #
            #     TRANSFERRED
            #     PROMOTED
            #     REPEATED
            #     WITHDRAWN
            #     GRADUATED
            #
            # naturally fall outside the active unique index.
            # ----------------------------------------------------------

            enrollment = StudentEnrollment(
                school_id=(
                    school.id
                    if school_id is None
                    else school_id
                ),
                student_id=student_obj.id,
                classroom_id=(
                    classroom_obj.id
                    if classroom_obj is not None
                    else None
                ),
                academic_session_id=session_obj.id,
                status=status,
                enrollment_date=enrollment_date,
                withdrawal_date=withdrawal_date,
                remarks=remarks,
                recorded_by=recorded_by,
            )

            _db.session.add(enrollment)
            _db.session.commit()

            _db.session.refresh(enrollment)
            _db.session.expunge(enrollment)

            return enrollment

    return _make


# ======================================================================
# 10. REPORT CARD FACTORIES
# ======================================================================

@pytest.fixture
def make_report_card(
    app,
    school,
    student,
    academic_session,
    term,
):

    def _make(
        student_obj=None,
        session_obj=None,
        term_obj=None,
        status=ReportCardStatus.DRAFT,
        public_reference=None,
        access_pin=None,
        summary_data=None,
        school_id=None,
    ):

        with app.app_context():

            student_obj = student_obj or student
            session_obj = session_obj or academic_session
            term_obj = term_obj or term

            report = ReportCard(
                school_id=(
                    school.id
                    if school_id is None
                    else school_id
                ),
                student_id=student_obj.id,
                academic_session_id=session_obj.id,
                term_id=term_obj.id,
                status=status,
                public_reference=(
                    public_reference
                    or secrets.token_urlsafe(16)
                ),
            )

            if summary_data is not None:
                report.summary_data = summary_data

            if access_pin is not None:
                report.set_access_pin(access_pin)

            _db.session.add(report)
            _db.session.commit()

            _db.session.refresh(report)
            _db.session.expunge(report)

            return report

    return _make

@pytest.fixture
def report_card(make_report_card):
    return make_report_card()


@pytest.fixture
def published_report_card(make_report_card):

    return make_report_card(
        status=ReportCardStatus.PUBLISHED,
        summary_data={
            "subject_scores": {},
            "overall_average": 75.0,
            "grade": "A",
            "remark": "Excellent",
        },
    )


@pytest.fixture
def published_report_card_with_pin(make_report_card):

    return make_report_card(
        status=ReportCardStatus.PUBLISHED,
        access_pin="1234",
        summary_data={
            "subject_scores": {},
            "overall_average": 75.0,
            "grade": "A",
            "remark": "Excellent",
        },
    )


# ======================================================================
# 11. STANDARD MODEL FIXTURES
# ======================================================================

@pytest.fixture
def base_user(make_user):
    return make_user("base")


@pytest.fixture
def teacher(make_teacher):
    return make_teacher("1")


@pytest.fixture
def sample_teacher(teacher):
    return teacher


@pytest.fixture
def teacher2(make_teacher):
    return make_teacher("2")


@pytest.fixture
def second_teacher(teacher2):
    return teacher2


@pytest.fixture
def student(make_student):
    return make_student("1")


@pytest.fixture
def student2(make_student):
    return make_student("2")


@pytest.fixture
def parent(make_parent):
    return make_parent("1")


@pytest.fixture
def subject(app, school):

    with app.app_context():

        subject = Subject(
            name="Mathematics",
            code="MATH101",
            school_id=school.id,
        )

        _db.session.add(subject)
        _db.session.commit()

        _db.session.refresh(subject)
        _db.session.expunge(subject)

        return subject


@pytest.fixture
def classroom(app, school):

    with app.app_context():

        classroom = Classroom(
            name="Room A",
            capacity=30,
            school_id=school.id,
        )

        _db.session.add(classroom)
        _db.session.commit()

        _db.session.refresh(classroom)
        _db.session.expunge(classroom)

        return classroom


@pytest.fixture
def academic_session(app, school):

    with app.app_context():

        session = AcademicSession(
            name="2026/2027",
            start_date=date(2026, 9, 1),
            end_date=date(2027, 6, 1),
            school_id=school.id,
            is_active=True,
        )

        _db.session.add(session)
        _db.session.commit()

        _db.session.refresh(session)
        _db.session.expunge(session)

        return session


@pytest.fixture
def term(app, academic_session, school):

    with app.app_context():

        term = Term(
            name="First Term",
            academic_session_id=academic_session.id,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 15),
            school_id=school.id,
        )

        _db.session.add(term)
        _db.session.commit()

        _db.session.refresh(term)
        _db.session.expunge(term)

        return term


@pytest.fixture
def exam(make_exam):
    return make_exam("1")


@pytest.fixture
def result(make_result):
    return make_result()


@pytest.fixture
def timetable(make_timetable):
    return make_timetable()


@pytest.fixture
def attendance_record(make_attendance):
    return make_attendance()


@pytest.fixture
def enrollment(make_enrollment):
    return make_enrollment()


@pytest.fixture
def notification(make_notification, student):
    return make_notification(student.user_id)


@pytest.fixture
def sample_absent_attendance(
    make_attendance,
    student,
    term,
):

    return make_attendance(
        student_obj=student,
        term_obj=term,
        date_val=date(2026, 9, 11),
        status=AttendanceStatus.ABSENT,
    )


@pytest.fixture
def sample_present_attendance(
    make_attendance,
    student,
    term,
):

    return make_attendance(
        student_obj=student,
        term_obj=term,
        date_val=date(2026, 9, 12),
        status=AttendanceStatus.PRESENT,
    )


@pytest.fixture
def student_in_teacher_classroom(
    app,
    teacher,
    classroom,
    student,
):

    with app.app_context():

        classroom_db = _db.session.merge(classroom)
        student_db = _db.session.merge(student)

        classroom_db.teacher_id = teacher.id
        student_db.classroom_id = classroom_db.id

        _db.session.commit()

        _db.session.refresh(student_db)
        _db.session.expunge(student_db)

        return student_db


# ======================================================================
# 12. JWT HELPERS
# ======================================================================

def _make_jwt_headers(app, user_id, role):

    with app.app_context():

        token = create_access_token(
            identity=str(user_id),
            additional_claims={
                "role": role,
            },
        )

    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


# ======================================================================
# 13. PLATFORM ADMIN AUTH
# ======================================================================

@pytest.fixture
def platform_admin_headers(app, make_user):

    user = make_user(
        suffix="platform_admin",
        role="platform_admin",
        school_id=None,
    )

    return _make_jwt_headers(
        app,
        user.id,
        "platform_admin",
    )


# ======================================================================
# 14. NORMAL ADMIN AUTH
# ======================================================================

@pytest.fixture
def admin_headers(app, db_session, school):

    admin = User(
        username="admin_test",
        email="admin_test@example.com",
        password="hashed-placeholder",
        role="admin",
        school_id=school.id,
    )

    db_session.add(admin)
    db_session.commit()

    return _make_jwt_headers(
        app,
        admin.id,
        "admin",
    )


@pytest.fixture
def admin_auth_headers(admin_headers):
    return admin_headers


@pytest.fixture
def admin_actor_id(app, admin_headers, school):

    with app.app_context():

        admin = User.query.filter_by(
            role="admin",
            school_id=school.id,
        ).first()

        if admin:
            return admin.id

        admin = User(
            username="service_admin",
            email="s_admin@example.com",
            password="hashed-placeholder",
            role="admin",
            school_id=school.id,
        )

        _db.session.add(admin)
        _db.session.commit()

        return admin.id


# ======================================================================
# 15. GENERIC AUTH HEADER FACTORY
# ======================================================================

@pytest.fixture
def auth_headers(app):

    def _get_headers(
        user_id=1,
        role="admin",
    ):

        return _make_jwt_headers(
            app,
            user_id,
            role,
        )

    return _get_headers


# ======================================================================
# 16. TEACHER AUTH
# ======================================================================

@pytest.fixture
def teacher_headers(app, teacher):

    return _make_jwt_headers(
        app,
        teacher.user_id,
        "teacher",
    )


# ======================================================================
# 17. STUDENT AUTH
# ======================================================================

@pytest.fixture
def student_headers(app, student):

    return _make_jwt_headers(
        app,
        student.user_id,
        "student",
    )


@pytest.fixture
def student2_headers(app, student2):

    return _make_jwt_headers(
        app,
        student2.user_id,
        "student",
    )


# ======================================================================
# 18. PARENT AUTH
# ======================================================================

@pytest.fixture
def parent_headers(app, parent):

    return _make_jwt_headers(
        app,
        parent.user_id,
        "parent",
    )


# ======================================================================
# 19. PASSWORD TEST USER
# ======================================================================

@pytest.fixture
def user_with_password(app, school):

    from school_app.utils.password import hash_password

    plain_password = "OriginalPass123"

    with app.app_context():

        user = User(
            username="pwtest_user",
            email="pwtest_user@example.com",
            password=hash_password(plain_password),
            role="student",
            school_id=school.id,
        )

        _db.session.add(user)
        _db.session.commit()

        token = create_access_token(
            identity=str(user.id),
            additional_claims={
                "role": "student",
            },
        )

        user_id = user.id

    return {
        "user_id": user_id,
        "plain_password": plain_password,
        "headers": {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    }
    
    
#==================================================================================================
#                        Onboarding progress fixtures
#==================================================================================================

@pytest.fixture
def make_onboarding_progress(app, school):

    def _make(**overrides):
        with app.app_context():
            progress = OnboardingProgress(school_id=school.id, **overrides)
            _db.session.add(progress)
            _db.session.commit()
            _db.session.refresh(progress)
            _db.session.expunge(progress)
            return progress

    return _make


@pytest.fixture
def onboarding_progress(make_onboarding_progress):
    return make_onboarding_progress()