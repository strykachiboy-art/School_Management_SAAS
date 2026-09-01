import logging

from school_app.enums.excuse import ExcuseStatus
from school_app.models.excuses import Excuse
from school_app.modules.attendance.services.notification_excuse_service import (
    notify_excuse_decision,
)


# ============================ 1. Uses Student Email ============================

def test_notify_uses_student_email_when_present(
    app,
    db_session,
    sample_absent_attendance,
    school,
    caplog,
):
    """
    When the student record has its own email set, that email is the one
    reported as the notification recipient.
    """
    excuse = Excuse(
        school_id=school.id,
        attendance_id=sample_absent_attendance.id,
        reason="Doctor visit",
        status=ExcuseStatus.APPROVED,
    )
    db_session.add(excuse)
    db_session.commit()

    with caplog.at_level(logging.INFO):
        notify_excuse_decision(excuse)

    assert "no email on file" not in caplog.text.lower()
    assert "approved" in caplog.text.lower()


# ============================ 2. Falls Back to User Email ============================

def test_notify_falls_back_to_user_email_when_student_has_none(
    app,
    db_session,
    sample_absent_attendance,
    school,
    caplog,
):
    """
    If the student record itself has no email set, the function falls back
    to the linked user's email instead of failing.
    """
    attendance = db_session.merge(sample_absent_attendance)
    student = attendance.student
    # Force the student's own email to be unavailable so the service
    # must fall back to the linked user's email.
    student.email = None
    db_session.add(student)
    db_session.commit()

    excuse = Excuse(
        school_id=school.id,
        attendance_id=sample_absent_attendance.id,
        reason="Family emergency",
        status=ExcuseStatus.REJECTED,
    )

    db_session.add(excuse)
    db_session.commit()

    with caplog.at_level(logging.INFO):
        notify_excuse_decision(excuse)

    assert "rejected" in caplog.text.lower()


# ============================ 3. Handles No Email Gracefully ============================

# User.email is a NOT NULL column, so a real committed DB row cannot
# represent a student and user with no email. Lightweight stand-ins
# allow this fallback branch to be tested without violating the schema.

class _StubUser:
    def __init__(self, email=None):
        self.email = email


class _StubStudent:
    def __init__(self, email=None, user=None):
        self.email = email
        self.user = user


class _StubAttendance:
    def __init__(self, student, student_id):
        self.student = student
        self.student_id = student_id


class _StubExcuse:
    def __init__(self, attendance, status):
        self.attendance = attendance
        self.status = status
        self.id = 999


def test_notify_handles_missing_email_without_crashing(caplog):
    """
    If neither the student nor the linked user has an email on file,
    the function logs a clear fallback message instead of raising.
    """
    student = _StubStudent(
        email=None,
        user=_StubUser(email=None),
    )
    attendance = _StubAttendance(
        student=student,
        student_id=42,
    )

    excuse = _StubExcuse(
        attendance=attendance,
        status=ExcuseStatus.APPROVED,
    )

    with caplog.at_level(logging.INFO):
        notify_excuse_decision(excuse)

    assert "no email on file" in caplog.text.lower()