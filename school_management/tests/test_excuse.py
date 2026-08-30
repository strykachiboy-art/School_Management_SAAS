from datetime import date, datetime, timedelta, timezone
from flask_jwt_extended import create_access_token
from school_app.enums.excuse import ExcuseStatus
from school_app.models.excuses import Excuse


# ============================ 1. Window Expiry Test ============================

def test_cannot_create_excuse_past_window_days(client, db_session, sample_absent_attendance, student_headers):
    """
    Cannot submit an excuse for an absence older than EXCUSE_REQUEST_WINDOW_DAYS (7 days).
    """
    sample_absent_attendance.date = (datetime.now(timezone.utc) - timedelta(days=8)).date()
    db_session.add(sample_absent_attendance)
    db_session.commit()

    res = client.post(
        "/excuses",
        json={
            "attendance_id": sample_absent_attendance.id,
            "reason": "Old absence excuse"
        },
        headers=student_headers
    )
    assert res.status_code == 400
    assert "within 7 days" in res.json["description"]


# ============================ 2. Duplicate Request Test ============================

def test_cannot_create_duplicate_excuse(client, db_session, sample_absent_attendance, student_headers):
    """
    Cannot submit a second excuse request for the same attendance record.
    """
    sample_absent_attendance = db_session.merge(sample_absent_attendance)
    sample_absent_attendance.date = date.today()
    db_session.add(sample_absent_attendance)
    db_session.commit()

    existing_excuse = Excuse(
        attendance_id=sample_absent_attendance.id,
        reason="First excuse",
        status=ExcuseStatus.PENDING
    )
    db_session.add(existing_excuse)
    db_session.commit()

    res = client.post(
        "/excuses",
        json={
            "attendance_id": sample_absent_attendance.id,
            "reason": "Second excuse attempt"
        },
        headers=student_headers
    )
    assert res.status_code == 400
    assert "already exists" in res.json["description"]


# ============================ 3. Authorization / Ownership Test ============================

def test_cannot_modify_other_student_excuse(client, db_session, sample_absent_attendance, student2):
    """
    A student cannot update an excuse belonging to another student.
    """
    sample_absent_attendance = db_session.merge(sample_absent_attendance)
    excuse = Excuse(
        attendance_id=sample_absent_attendance.id,
        reason="Original student excuse",
        status=ExcuseStatus.PENDING
    )
    db_session.add(excuse)
    db_session.commit()

    token = create_access_token(identity=str(student2.user_id), additional_claims={"role": "student"})
    other_headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    res = client.patch(
        f"/excuses/{excuse.id}",
        json={"reason": "Hijack attempt"},
        headers=other_headers
    )
    assert res.status_code == 403
    assert "manage your own excuse" in res.json["description"]


# ============================ 4. Bulk Review Test ============================

def test_bulk_review_excuses_success(client, db_session, sample_absent_attendance, teacher_headers):
    """
    Teacher can bulk approve multiple pending excuses in a single call via /excuses/bulk-approve.
    """
    sample_absent_attendance = db_session.merge(sample_absent_attendance)
    sample_absent_attendance.date = date.today()
    db_session.add(sample_absent_attendance)
    db_session.commit()

    excuse1 = Excuse(
        attendance_id=sample_absent_attendance.id,
        reason="Excuse 1",
        status=ExcuseStatus.PENDING
    )
    db_session.add(excuse1)
    db_session.commit()

    payload = {
        "excuse_ids": [excuse1.id]
    }

    res = client.post(
        "/excuses/bulk-approve",
        json=payload,
        headers=teacher_headers
    )
    assert res.status_code == 200

    db_session.refresh(excuse1)
    assert excuse1.status == ExcuseStatus.APPROVED