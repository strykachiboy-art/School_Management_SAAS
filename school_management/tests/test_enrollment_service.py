from datetime import datetime, timedelta, timezone

import pytest

from school_app.enums.enrollment import EnrollmentStatus
from school_app.extensions import db
from school_app.models.academic_session import AcademicSession
from school_app.models.student_enrollment import StudentEnrollment
from school_app.modules.people.services.enrollment_service import (
    _get_current_session_id,
    get_current_enrollment,
    get_enrollment_history,
    record_enrollment,
)


def utcnow():
    return datetime.now(timezone.utc)


# ======================================================================
# _get_current_session_id
# ======================================================================


def test_get_current_session_id_returns_active_session(
    app,
    academic_session,
):
    with app.app_context():
        academic_session_db = db.session.get(
            AcademicSession,
            academic_session.id,
        )

        academic_session_db.is_active = True
        db.session.commit()

        result = _get_current_session_id(
            school_id=academic_session.school_id,
        )

        assert result == academic_session.id


def test_get_current_session_id_returns_none_when_no_active_session(
    app,
    academic_session,
):
    with app.app_context():
        academic_session_db = db.session.get(
            AcademicSession,
            academic_session.id,
        )

        academic_session_db.is_active = False
        db.session.commit()

        result = _get_current_session_id(
            school_id=academic_session.school_id,
        )

        assert result is None


# ======================================================================
# get_current_enrollment
# ======================================================================


def test_get_current_enrollment_returns_active_enrollment(
    app,
    student,
    classroom,
    academic_session,
    make_enrollment,
):
    with app.app_context():
        enrollment = make_enrollment(
            student_obj=student,
            classroom_obj=classroom,
            session_obj=academic_session,
            status=EnrollmentStatus.ACTIVE,
        )

        current = get_current_enrollment(student.id)

        assert current is not None
        assert current.id == enrollment.id
        assert current.student_id == student.id
        assert current.withdrawal_date is None


def test_get_current_enrollment_returns_none_when_withdrawn(
    app,
    student,
    classroom,
    academic_session,
    make_enrollment,
):
    with app.app_context():
        enrollment = make_enrollment(
            student_obj=student,
            classroom_obj=classroom,
            session_obj=academic_session,
            status=EnrollmentStatus.WITHDRAWN,
            withdrawal_date_val=utcnow(),
        )

        current = get_current_enrollment(student.id)

        assert current is None


# ======================================================================
# get_enrollment_history
# ======================================================================


def test_get_enrollment_history_returns_latest_first(
    app,
    student,
    classroom,
    academic_session,
    make_enrollment,
):
    with app.app_context():
        first_date = datetime(
            2026,
            9,
            1,
            8,
            0,
            tzinfo=timezone.utc,
        )

        second_date = first_date + timedelta(days=10)

        first = make_enrollment(
            student_obj=student,
            classroom_obj=classroom,
            session_obj=academic_session,
            status=EnrollmentStatus.TRANSFERRED,
            enrollment_date_val=first_date,
        )

        second = make_enrollment(
            student_obj=student,
            classroom_obj=classroom,
            session_obj=academic_session,
            status=EnrollmentStatus.ACTIVE,
            enrollment_date_val=second_date,
        )

        history = get_enrollment_history(student.id)

        assert len(history) == 2

        assert history[0].id == second.id
        assert history[1].id == first.id

        assert history[0].enrollment_date >= history[1].enrollment_date


def test_get_enrollment_history_returns_empty_list_for_student_without_history(
    app,
    student,
):
    with app.app_context():
        history = get_enrollment_history(student.id)

        assert history == []


# ======================================================================
# record_enrollment
# ======================================================================


def test_record_enrollment_returns_none_without_classroom(
    app,
    student,
    academic_session,
):
    with app.app_context():
        result = record_enrollment(
            student_id=student.id,
            classroom_id=None,
            academic_session_id=academic_session.id,
        )

        assert result is None


def test_record_enrollment_returns_none_without_academic_session(
    app,
    student,
    classroom,
):
    with app.app_context():
        result = record_enrollment(
            student_id=student.id,
            classroom_id=classroom.id,
            academic_session_id=None,
        )

        assert result is None


def test_record_enrollment_uses_classroom_school_id(
    app,
    student,
    classroom,
    academic_session,
):
    with app.app_context():
        result = record_enrollment(
            student_id=student.id,
            classroom_id=classroom.id,
            academic_session_id=academic_session.id,
        )

        assert result is not None
        assert result.school_id == classroom.school_id
        assert result.student_id == student.id
        assert result.classroom_id == classroom.id
        assert result.academic_session_id == academic_session.id
        assert result.status == EnrollmentStatus.ACTIVE


def test_record_enrollment_creates_active_enrollment(
    app,
    student,
    classroom,
    academic_session,
):
    with app.app_context():
        result = record_enrollment(
            student_id=student.id,
            classroom_id=classroom.id,
            academic_session_id=academic_session.id,
            remarks="Initial enrollment",
        )

        assert result is not None
        assert result.id is not None
        assert result.student_id == student.id
        assert result.classroom_id == classroom.id
        assert result.academic_session_id == academic_session.id
        assert result.status == EnrollmentStatus.ACTIVE
        assert result.withdrawal_date is None
        assert result.remarks == "Initial enrollment"


def test_record_enrollment_auto_detects_school_from_classroom(
    app,
    student,
    classroom,
    academic_session,
):
    with app.app_context():
        result = record_enrollment(
            student_id=student.id,
            classroom_id=classroom.id,
            academic_session_id=academic_session.id,
            school_id=None,
        )

        assert result is not None
        assert result.school_id == classroom.school_id


def test_record_enrollment_auto_detects_current_session(
    app,
    student,
    classroom,
    academic_session,
):
    with app.app_context():
        session_db = db.session.get(
            AcademicSession,
            academic_session.id,
        )

        session_db.is_active = True
        db.session.commit()

        result = record_enrollment(
            student_id=student.id,
            classroom_id=classroom.id,
            academic_session_id=None,
        )

        assert result is not None
        assert result.academic_session_id == academic_session.id


def test_record_enrollment_withdraws_existing_current_enrollment(
    app,
    student,
    classroom,
    academic_session,
    make_classroom,
):
    with app.app_context():
        old_enrollment = record_enrollment(
            student_id=student.id,
            classroom_id=classroom.id,
            academic_session_id=academic_session.id,
            remarks="Original enrollment",
        )

        assert old_enrollment is not None

        new_classroom = make_classroom("Transfer")

        new_enrollment = record_enrollment(
            student_id=student.id,
            classroom_id=new_classroom.id,
            academic_session_id=academic_session.id,
            remarks="Transferred to another classroom",
        )

        assert new_enrollment is not None

        db.session.refresh(old_enrollment)
        db.session.refresh(new_enrollment)

        assert old_enrollment.withdrawal_date is not None
        assert old_enrollment.status == EnrollmentStatus.TRANSFERRED

        assert new_enrollment.withdrawal_date is None
        assert new_enrollment.status == EnrollmentStatus.ACTIVE

        assert new_enrollment.classroom_id == new_classroom.id

        history = get_enrollment_history(student.id)

        assert len(history) == 2
        assert history[0].id == new_enrollment.id
        assert history[1].id == old_enrollment.id


def test_record_enrollment_closes_existing_enrollment_with_explicit_status(
    app,
    student,
    classroom,
    academic_session,
    make_classroom,
):
    with app.app_context():
        old_enrollment = record_enrollment(
            student_id=student.id,
            classroom_id=classroom.id,
            academic_session_id=academic_session.id,
        )

        new_classroom = make_classroom("New")

        new_enrollment = record_enrollment(
            student_id=student.id,
            classroom_id=new_classroom.id,
            academic_session_id=academic_session.id,
            status=EnrollmentStatus.WITHDRAWN,
        )

        assert old_enrollment.id != new_enrollment.id

        old_enrollment_db = db.session.get(
            StudentEnrollment,
            old_enrollment.id,
        )

        new_enrollment_db = db.session.get(
            StudentEnrollment,
            new_enrollment.id,
        )

        assert old_enrollment_db.status == EnrollmentStatus.WITHDRAWN
        assert old_enrollment_db.withdrawal_date is not None

        assert new_enrollment_db.status == EnrollmentStatus.WITHDRAWN
        assert new_enrollment_db.classroom_id == new_classroom.id


def test_record_enrollment_preserves_remarks(
    app,
    student,
    classroom,
    academic_session,
):
    with app.app_context():
        enrollment = record_enrollment(
            student_id=student.id,
            classroom_id=classroom.id,
            academic_session_id=academic_session.id,
            remarks="Promoted to next class",
        )

        assert enrollment.remarks == "Promoted to next class"


def test_record_enrollment_records_recorded_by(
    app,
    student,
    classroom,
    academic_session,
):
    with app.app_context():
        recorded_by = 12345

        enrollment = record_enrollment(
            student_id=student.id,
            classroom_id=classroom.id,
            academic_session_id=academic_session.id,
            recorded_by=recorded_by,
        )

        assert enrollment.recorded_by == recorded_by


def test_record_enrollment_returns_none_when_no_current_session(
    app,
    student,
    classroom,
):
    with app.app_context():
        result = record_enrollment(
            student_id=student.id,
            classroom_id=classroom.id,
            academic_session_id=None,
        )

        assert result is None


def test_record_enrollment_creates_multiple_history_records_in_same_session(
    app,
    student,
    classroom,
    academic_session,
    make_classroom,
):
    """
    A student can have multiple enrollment records during the same
    academic session because classroom transfers must be preserved
    in enrollment history.
    """
    with app.app_context():
        first = record_enrollment(
            student_id=student.id,
            classroom_id=classroom.id,
            academic_session_id=academic_session.id,
            remarks="Initial classroom",
        )

        second_classroom = make_classroom("Second")

        second = record_enrollment(
            student_id=student.id,
            classroom_id=second_classroom.id,
            academic_session_id=academic_session.id,
            remarks="Transferred classroom",
        )

        assert first.id != second.id

        history = get_enrollment_history(student.id)

        assert len(history) == 2

        assert history[0].id == second.id
        assert history[1].id == first.id

        assert history[0].classroom_id == second_classroom.id
        assert history[1].classroom_id == classroom.id

        assert history[1].withdrawal_date is not None
        assert history[0].withdrawal_date is None
        
        
