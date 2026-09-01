from datetime import date, datetime, timedelta, timezone
from flask_jwt_extended import create_access_token

from school_app.enums.attendance import AttendanceStatus
from school_app.enums.excuse import ExcuseStatus
from school_app.models.attendance import Attendance
from school_app.models.excuses import Excuse


# ======================================================================
# Helpers
# ======================================================================

def _prepare_absent_attendance(db_session, attendance):
    """
    Re-attach the attendance record to the current SQLAlchemy session,
    make it a valid ABSENT record for the excuse tests, and commit it.
    """
    attendance = db_session.merge(attendance)
    attendance.date = date.today()
    attendance.status = AttendanceStatus.ABSENT

    db_session.add(attendance)
    db_session.commit()
    db_session.refresh(attendance)

    return attendance


def _make_excuse(db_session, attendance, reason="Test excuse"):
    """
    Create a valid Excuse using the same school as its Attendance record.
    Excuse.school_id is required by the model.
    """
    attendance = db_session.merge(attendance)

    excuse = Excuse(
        school_id=attendance.school_id,
        attendance_id=attendance.id,
        reason=reason,
        status=ExcuseStatus.PENDING,
    )

    db_session.add(excuse)
    db_session.commit()
    db_session.refresh(excuse)

    return excuse


# ======================================================================
# 1. Window Expiry Test
# ======================================================================

def test_cannot_create_excuse_past_window_days(
    client,
    db_session,
    sample_absent_attendance,
    student_headers,
):
    """
    Cannot submit an excuse for an absence older than
    EXCUSE_REQUEST_WINDOW_DAYS (7 days).
    """
    attendance = db_session.merge(sample_absent_attendance)
    attendance.date = (
        datetime.now(timezone.utc) - timedelta(days=8)
    ).date()

    attendance.status = AttendanceStatus.ABSENT

    db_session.add(attendance)
    db_session.commit()

    res = client.post(
        "/excuses",
        json={
            "attendance_id": attendance.id,
            "reason": "Old absence excuse",
        },
        headers=student_headers,
    )

    assert res.status_code == 400
    assert "within 7 days" in res.json["description"]


# ======================================================================
# 2. Duplicate Request Test
# ======================================================================

def test_cannot_create_duplicate_excuse(
    client,
    db_session,
    sample_absent_attendance,
    student_headers,
):
    """
    Cannot submit a second excuse request for the same attendance record.
    """
    attendance = _prepare_absent_attendance(
        db_session,
        sample_absent_attendance,
    )
    existing_excuse = _make_excuse(
        db_session,
        attendance,
        reason="First excuse",
    )

    res = client.post(
        "/excuses",
        json={
            "attendance_id": attendance.id,
            "reason": "Second excuse attempt",
        },
        headers=student_headers,
    )

    assert res.status_code == 400
    assert "already exists" in res.json["description"]

    db_session.refresh(existing_excuse)

    assert existing_excuse.status == ExcuseStatus.PENDING


# ======================================================================
# 3. Authorization / Ownership Test
# ======================================================================

def test_cannot_modify_other_student_excuse(
    client,
    db_session,
    sample_absent_attendance,
    student2,
):
    """
    A student cannot update an excuse belonging to another student.
    """
    attendance = _prepare_absent_attendance(
        db_session,
        sample_absent_attendance,
    )
    excuse = _make_excuse(
        db_session,
        attendance,
        reason="Original student excuse",
    )

    token = create_access_token(
        identity=str(student2.user_id),
        additional_claims={
            "role": "student",
        },
    )

    other_headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    res = client.patch(
        f"/excuses/{excuse.id}",
        json={
            "reason": "Hijack attempt",
        },
        headers=other_headers,
    )

    assert res.status_code == 403
    assert "manage your own excuse" in res.json["description"]

    db_session.refresh(excuse)

    assert excuse.reason == "Original student excuse"
    assert excuse.status == ExcuseStatus.PENDING


# ======================================================================
# 4. Bulk Review Test
# ======================================================================

def test_bulk_review_excuses_success(
    client,
    db_session,
    sample_absent_attendance,
    teacher_headers,
):
    """
    Teacher can bulk approve multiple pending excuses in a single call
    via /excuses/bulk-approve.
    """
    attendance = _prepare_absent_attendance(
        db_session,
        sample_absent_attendance,
    )
    excuse1 = _make_excuse(
        db_session,
        attendance,
        reason="Excuse 1",
    )

    payload = {
        "excuse_ids": [excuse1.id],
    }

    res = client.post(
        "/excuses/bulk-approve",
        json=payload,
        headers=teacher_headers,
    )

    assert res.status_code == 200

    assert excuse1.id in res.json["reviewed"]

    db_session.refresh(excuse1)

    assert excuse1.status == ExcuseStatus.APPROVED

    attendance = db_session.get(
        Attendance,
        attendance.id,
    )
    assert attendance.status == AttendanceStatus.EXCUSED