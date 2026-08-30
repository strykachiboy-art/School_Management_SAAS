from datetime import date
from school_app.enums.excuse import ExcuseStatus
from school_app.models.excuses import Excuse


def _make_pending_excuse(db_session, attendance, reason="Doctor's appointment"):
    attendance = db_session.merge(attendance)
    attendance.date = date.today()
    db_session.add(attendance)
    db_session.commit()

    excuse = Excuse(
        attendance_id=attendance.id,
        reason=reason,
        status=ExcuseStatus.PENDING,
    )
    db_session.add(excuse)
    db_session.commit()
    db_session.refresh(excuse)
    return excuse


# ============================ GET /excuses/<id> ============================

def test_get_excuse_by_id(client, db_session, sample_absent_attendance, admin_headers):
    excuse = _make_pending_excuse(db_session, sample_absent_attendance)

    res = client.get(f"/excuses/{excuse.id}", headers=admin_headers)

    assert res.status_code == 200
    assert res.json["id"] == excuse.id
    assert res.json["status"] == "pending"


def test_get_excuse_not_found(client, admin_headers):
    res = client.get("/excuses/999999", headers=admin_headers)

    assert res.status_code == 404


# ============================ GET /excuses (list) ============================

def test_list_excuses(client, db_session, sample_absent_attendance, admin_headers):
    _make_pending_excuse(db_session, sample_absent_attendance)

    res = client.get("/excuses", headers=admin_headers)

    assert res.status_code == 200
    assert isinstance(res.json, list)
    assert len(res.json) >= 1


def test_list_excuses_filter_by_status(client, db_session, sample_absent_attendance, admin_headers):
    _make_pending_excuse(db_session, sample_absent_attendance)

    res = client.get("/excuses?status=approved", headers=admin_headers)

    assert res.status_code == 200
    assert res.json == []


def test_list_excuses_invalid_status(client, admin_headers):
    res = client.get("/excuses?status=not_a_real_status", headers=admin_headers)

    assert res.status_code == 400


# ============================ DELETE /excuses/<id> ============================

def test_delete_own_pending_excuse(client, db_session, sample_absent_attendance, student_headers):
    excuse = _make_pending_excuse(db_session, sample_absent_attendance)

    res = client.delete(f"/excuses/{excuse.id}", headers=student_headers)

    assert res.status_code == 200
    assert db_session.get(Excuse, excuse.id) is None


def test_cannot_delete_other_student_excuse(client, db_session, sample_absent_attendance, student2):
    from flask_jwt_extended import create_access_token

    excuse = _make_pending_excuse(db_session, sample_absent_attendance)

    token = create_access_token(identity=str(student2.user_id), additional_claims={"role": "student"})
    other_headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    res = client.delete(f"/excuses/{excuse.id}", headers=other_headers)

    assert res.status_code == 403


# ============================ POST /excuses/<id>/approve ============================

def test_approve_excuse(client, db_session, sample_absent_attendance, teacher_headers):
    excuse = _make_pending_excuse(db_session, sample_absent_attendance)

    res = client.post(f"/excuses/{excuse.id}/approve", headers=teacher_headers)

    assert res.status_code == 200
    assert res.json["status"] == "approved"


def test_approve_already_reviewed_excuse_fails(client, db_session, sample_absent_attendance, teacher_headers):
    excuse = _make_pending_excuse(db_session, sample_absent_attendance)
    client.post(f"/excuses/{excuse.id}/approve", headers=teacher_headers)

    res = client.post(f"/excuses/{excuse.id}/approve", headers=teacher_headers)

    assert res.status_code == 400


def test_student_cannot_approve_excuse(client, db_session, sample_absent_attendance, student_headers):
    excuse = _make_pending_excuse(db_session, sample_absent_attendance)

    res = client.post(f"/excuses/{excuse.id}/approve", headers=student_headers)

    assert res.status_code == 403


# ============================ POST /excuses/<id>/reject ============================

def test_reject_excuse(client, db_session, sample_absent_attendance, teacher_headers):
    excuse = _make_pending_excuse(db_session, sample_absent_attendance)

    res = client.post(f"/excuses/{excuse.id}/reject", headers=teacher_headers)

    assert res.status_code == 200
    assert res.json["status"] == "rejected"


# ============================ POST /excuses/bulk-reject ============================

def test_bulk_reject_excuses(client, db_session, sample_absent_attendance, teacher_headers):
    excuse = _make_pending_excuse(db_session, sample_absent_attendance)

    res = client.post(
        "/excuses/bulk-reject",
        json={"excuse_ids": [excuse.id]},
        headers=teacher_headers,
    )

    assert res.status_code == 200
    assert excuse.id in res.json["reviewed"]

    db_session.refresh(excuse)
    assert excuse.status == ExcuseStatus.REJECTED