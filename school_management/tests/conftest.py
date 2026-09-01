import uuid
from datetime import date, time

import pytest

from school_app import create_app
from school_app.enums.attendance import AttendanceStatus
from school_app.enums.day_of_week import DayOfWeek
from school_app.enums.notification import NotificationType
from school_app.extensions import db as _db, limiter, redis_client
from school_app.models.academic_session import AcademicSession
from school_app.models.academic_stage import AcademicStage
from school_app.models.attendance import Attendance
from school_app.models.classroom import Classroom
from school_app.models.exam import Exam
from school_app.models.notification import Notification
from school_app.models.parent_guardian import ParentGuardian
from school_app.models.result import Result
from school_app.models.school import School
from school_app.models.student import Student
from school_app.models.subject import Subject
from school_app.models.teacher import Teacher
from school_app.models.term import Term
from school_app.models.timetable import Timetable
from school_app.models.user import User


# ----------------------------------------------------------------------
# 1. Global Setup & Teardown Fixtures
# ----------------------------------------------------------------------

@pytest.fixture(scope="function")
def app():
    """
    Create a completely isolated Flask app with an in-memory SQLite
    database for every test.

    Because this fixture is function-scoped, every test gets a brand-new
    database. Therefore, a separate autouse clean_database fixture is
    NOT necessary.
    """
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JWT_SECRET_KEY": "test-secret-key-that-is-at-least-32-bytes-long",
        "RATELIMIT_ENABLED": True,
        "RATELIMIT_STORAGE_URI": "memory://",
        "WTF_CSRF_ENABLED": False,
        "ADMIN_ACCESS_ENABLED": True,
    }

    app = create_app(config=test_config)

    with app.app_context():
        _db.create_all()

        yield app

        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="function")
def db(app):
    """Provides the SQLAlchemy db instance for direct test manipulations."""
    return _db


@pytest.fixture(scope="function")
def db_session(app, db):
    """Provides convenient access to db.session."""
    return db.session


@pytest.fixture(scope="function")
def school(app):
    """Creates a default tenant School that other fixtures attach to."""
    with app.app_context():
        s = School(
            name="Test School",
            slug="test-school",
        )

        _db.session.add(s)
        _db.session.commit()

        _db.session.refresh(s)
        _db.session.expunge(s)

        return s


@pytest.fixture(autouse=True)
def auto_clear_limiter(app):
    """Automatically resets Flask-Limiter state between tests."""
    yield

    with app.app_context():
        if getattr(limiter, "_storage", None) is not None:
            try:
                limiter.reset()
            except Exception:
                pass


@pytest.fixture(autouse=True)
def auto_clear_redis(app):
    """Cleans up Redis refresh-whitelist keys after each test."""
    yield

    with app.app_context():
        try:
            keys = redis_client.keys("refresh_whitelist:*")

            if keys:
                redis_client.delete(*keys)

        except Exception:
            pass


# ----------------------------------------------------------------------
# 2. HTTP Client Helpers
# ----------------------------------------------------------------------

@pytest.fixture(scope="function")
def client(app):
    return app.test_client()


@pytest.fixture
def json_client(client):
    """A test client wrapper that attaches Accept: application/json."""

    class JSONClient:
        def __init__(self, c):
            self.c = c
            self.headers = {
                "Accept": "application/json"
            }

        def _kwargs(self, kwargs):
            kwargs["headers"] = {
                **self.headers,
                **kwargs.get("headers", {}),
            }
            return kwargs

        def post(self, url, **kwargs):
            return self.c.post(url, **self._kwargs(kwargs))

        def patch(self, url, **kwargs):
            return self.c.patch(url, **self._kwargs(kwargs))

        def put(self, url, **kwargs):
            return self.c.put(url, **self._kwargs(kwargs))

        def get(self, url, **kwargs):
            return self.c.get(url, **self._kwargs(kwargs))

        def delete(self, url, **kwargs):
            return self.c.delete(url, **self._kwargs(kwargs))

    return JSONClient(client)


@pytest.fixture
def admin_client(client, admin_headers):
    """A test client wrapper that automatically attaches admin auth headers."""

    class AdminClient:
        def __init__(self, c):
            self.c = c
            self.headers = admin_headers

        def _kwargs(self, kwargs):
            kwargs["headers"] = {
                **self.headers,
                **kwargs.get("headers", {}),
            }
            return kwargs

        def post(self, url, **kwargs):
            return self.c.post(url, **self._kwargs(kwargs))

        def patch(self, url, **kwargs):
            return self.c.patch(url, **self._kwargs(kwargs))

        def put(self, url, **kwargs):
            return self.c.put(url, **self._kwargs(kwargs))

        def get(self, url, **kwargs):
            return self.c.get(url, **self._kwargs(kwargs))

        def delete(self, url, **kwargs):
            return self.c.delete(url, **self._kwargs(kwargs))

    return AdminClient(client)


# ----------------------------------------------------------------------
# 3. Academic Stage Fixture
# ----------------------------------------------------------------------

@pytest.fixture
def admin_stage(app, school):
    """Creates a default AcademicStage bound to the test school."""
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


# ----------------------------------------------------------------------
# 4. Model Factories
# ----------------------------------------------------------------------

@pytest.fixture
def make_notification(app):
    """Factory fixture for creating Notification records."""

    def _make(
        recipient_user_id,
        title="Test Notification",
        message="Test message",
        notification_type=NotificationType.GENERAL,
        is_read=False,
    ):
        with app.app_context():
            n = Notification(
                recipient_id=recipient_user_id,
                title=title,
                message=message,
                notification_type=notification_type,
                is_read=is_read,
            )

            _db.session.add(n)
            _db.session.commit()

            _db.session.refresh(n)
            _db.session.expunge(n)

            return n

    return _make


@pytest.fixture
def notification(make_notification, student):
    """Standard notification fixture owned by the student's user."""
    return make_notification(student.user_id)


@pytest.fixture
def make_user(app, school):
    """
    Factory for creating users belonging to the test school.

    Every user is tenant-aware by default.
    """

    def _make(suffix="1", role="student"):
        with app.app_context():
            user = User(
                username=f"user_{suffix}",
                email=f"user_{suffix}@example.com",
                password="hashed-placeholder",
                role=role,
                school_id=school.id,
            )

            _db.session.add(user)
            _db.session.commit()

            _db.session.refresh(user)
            _db.session.expunge(user)

            return user

    return _make


@pytest.fixture
def make_teacher(app, school):
    """Factory fixture for creating teachers in the test school."""

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
            _db.session.commit()

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
    """Factory fixture for creating students in the test school."""

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
            _db.session.commit()

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
    """Factory fixture for creating parent/guardian records."""

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
            _db.session.commit()

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


@pytest.fixture
def make_classroom(app, school):
    """Factory fixture for creating classrooms in the test school."""

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
def make_exam(
    app,
    subject,
    classroom,
    academic_session,
    school,
    term,
):
    """Factory fixture for creating exams."""

    def _make(
        suffix="1",
        subject_obj=subject,
        classroom_obj=classroom,
        session_obj=academic_session,
        term_obj=term,
        exam_date_val=date(2026, 12, 1),
        start_time_val=time(9, 0),
        duration_minutes=90,
        total_marks=100,
    ):
        with app.app_context():
            exam = Exam(
                school_id=school.id,
                title=f"Exam {suffix}",
                description="Test description",
                subject_id=subject_obj.id,
                classroom_id=classroom_obj.id,
                session_id=session_obj.id,
                term_id=term_obj.id if term_obj else None,
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
    """Factory fixture for creating results."""

    def _make(
        student_obj=student,
        exam_obj=exam,
        marks=85.5,
    ):
        with app.app_context():
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
    """
    Factory fixture for creating Timetable entries.

    All related records belong to the same test school by default.
    """

    def _make(
        term_obj=term,
        classroom_obj=classroom,
        subject_obj=subject,
        teacher_obj=teacher,
        school_id=None,
        day_of_week=DayOfWeek.MONDAY,
        start_time_val=time(8, 0),
        end_time_val=time(9, 0),
    ):
        with app.app_context():
            timetable = Timetable(
                school_id=school_id or school.id,
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
    """Factory fixture for creating attendance records."""

    def _make(
        student_obj=student,
        term_obj=term,
        date_val=date(2026, 9, 10),
        status=AttendanceStatus.PRESENT,
    ):
        with app.app_context():
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


# ----------------------------------------------------------------------
# 5. Standard Model Fixtures
# ----------------------------------------------------------------------

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
    """
    Separate teacher used by timetable classroom-conflict tests.

    This is intentionally different from the default `teacher` fixture.
    """
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
        subj = Subject(
            name="Mathematics",
            code="MATH101",
            school_id=school.id,
        )

        _db.session.add(subj)
        _db.session.commit()

        _db.session.refresh(subj)
        _db.session.expunge(subj)

        return subj


@pytest.fixture
def classroom(app, school):
    with app.app_context():
        cls = Classroom(
            name="Room A",
            capacity=30,
            school_id=school.id,
        )

        _db.session.add(cls)
        _db.session.commit()

        _db.session.refresh(cls)
        _db.session.expunge(cls)

        return cls


@pytest.fixture
def academic_session(app, school):
    with app.app_context():
        session = AcademicSession(
            name="2026/2027",
            start_date=date(2026, 9, 1),
            end_date=date(2027, 6, 1),
            school_id=school.id,
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
    """Standard timetable fixture."""
    return make_timetable()


@pytest.fixture
def attendance_record(make_attendance):
    return make_attendance()


@pytest.fixture
def sample_absent_attendance(make_attendance, student, term):
    """Fixture providing an attendance record with ABSENT status."""
    return make_attendance(
        student_obj=student,
        term_obj=term,
        date_val=date(2026, 9, 11),
        status=AttendanceStatus.ABSENT,
    )


@pytest.fixture
def sample_present_attendance(make_attendance, student, term):
    """Fixture providing an attendance record with PRESENT status."""
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
        c = _db.session.merge(classroom)
        s = _db.session.merge(student)

        c.teacher_id = teacher.id
        s.classroom_id = c.id

        _db.session.commit()

        _db.session.refresh(s)
        _db.session.expunge(s)

        return s


# ----------------------------------------------------------------------
# 6. Auth / Header Fixtures
# ----------------------------------------------------------------------

@pytest.fixture(scope="function")
def admin_actor_id(app, admin_headers, school):
    """
    Returns the user ID of an admin for direct service testing requiring
    actor_id.
    """
    with app.app_context():
        admin = User.query.filter_by(
            role="admin",
            school_id=school.id,
        ).first()

        if admin:
            return admin.id

        new_admin = User(
            username="service_admin",
            email="s_admin@example.com",
            password="hashed-placeholder",
            role="admin",
            school_id=school.id,
        )

        _db.session.add(new_admin)
        _db.session.commit()

        return new_admin.id


@pytest.fixture(scope="function")
def auth_headers(app):
    """Dynamic factory for generating JWT authorization headers."""

    from flask_jwt_extended import create_access_token

    def _get_headers(user_id=1, role="admin"):
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

    return _get_headers


@pytest.fixture(scope="function")
def admin_headers(app, db_session, school):
    from flask_jwt_extended import create_access_token

    admin = User(
        username="admin_test",
        email="admin_test@example.com",
        password="hashed-placeholder",
        role="admin",
        school_id=school.id,
    )

    db_session.add(admin)
    db_session.commit()

    token = create_access_token(
        identity=str(admin.id),
        additional_claims={
            "role": "admin",
        },
    )

    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


@pytest.fixture(scope="function")
def admin_auth_headers(admin_headers):
    """Alias for admin_headers."""
    return admin_headers


@pytest.fixture(scope="function")
def teacher_headers(app, teacher):
    from flask_jwt_extended import create_access_token

    with app.app_context():
        token = create_access_token(
            identity=str(teacher.user_id),
            additional_claims={
                "role": "teacher",
            },
        )

    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


@pytest.fixture(scope="function")
def student_headers(app, student):
    from flask_jwt_extended import create_access_token

    with app.app_context():
        token = create_access_token(
            identity=str(student.user_id),
            additional_claims={
                "role": "student",
            },
        )

    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


@pytest.fixture(scope="function")
def student2_headers(app, student2):
    from flask_jwt_extended import create_access_token

    with app.app_context():
        token = create_access_token(
            identity=str(student2.user_id),
            additional_claims={
                "role": "student",
            },
        )

    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


@pytest.fixture(scope="function")
def parent_headers(app, parent):
    from flask_jwt_extended import create_access_token

    with app.app_context():
        token = create_access_token(
            identity=str(parent.user_id),
            additional_claims={
                "role": "parent",
            },
        )

    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


@pytest.fixture(scope="function")
def user_with_password(app, school):
    from flask_jwt_extended import create_access_token
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
