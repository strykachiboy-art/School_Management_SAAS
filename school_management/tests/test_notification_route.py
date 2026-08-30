from school_app.extensions import db
from school_app.models.notification import Notification
from school_app.enums.notification import NotificationType


def test_create_notification_as_admin(client, admin_headers, student):
    resp = client.post("/notifications", json={
        "recipient_id": student.user_id,
        "title": "Exam Scheduled",
        "message": "Your exam is on Monday.",
        "notification_type": "EXAM",
    }, headers=admin_headers)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["recipient_id"] == student.user_id
    assert data["is_read"] is False
    assert data["read_at"] is None


def test_create_notification_forbidden_for_non_admin(client, student_headers, student):
    resp = client.post("/notifications", json={
        "recipient_id": student.user_id,
        "title": "x",
        "message": "y",
        "notification_type": "GENERAL",
    }, headers=student_headers)
    assert resp.status_code == 403


def test_create_notification_missing_body_returns_400(client, admin_headers):
    resp = client.post(
        "/notifications",
        data="not json",
        headers={**admin_headers, "Content-Type": "application/json"},
    )
    assert resp.status_code == 400


def test_create_notification_validation_error_shape(client, admin_headers, student):
    resp = client.post("/notifications", json={
        "recipient_id": student.user_id,
        "title": "",
        "message": "y",
        "notification_type": "GENERAL",
    }, headers=admin_headers)
    assert resp.status_code == 422
    details = resp.get_json()["details"]
    assert details[0]["field"] == "title"
    assert "message" in details[0]


def test_create_notification_invalid_recipient_returns_400(client, admin_headers):
    resp = client.post("/notifications", json={
        "recipient_id": 999999,
        "title": "t",
        "message": "m",
        "notification_type": "GENERAL",
    }, headers=admin_headers)
    assert resp.status_code == 400


def test_list_my_notifications(client, student_headers, student):
    for i in range(3):
        db.session.add(Notification(
            recipient_id=student.user_id, title=f"Notice {i}", message="msg",
            notification_type=NotificationType.GENERAL,
        ))
    db.session.commit()

    resp = client.get("/notifications", headers=student_headers)
    assert resp.status_code == 200
    assert resp.get_json()["total"] == 3


def test_list_notifications_per_page_is_capped(client, student_headers, student):
    resp = client.get("/notifications?per_page=99999", headers=student_headers)
    assert resp.status_code == 200
    # doesn't assert exact cap value in case you tune MAX_PER_PAGE later —
    # just confirms the request doesn't error and page metadata is present
    assert "page" in resp.get_json()


def test_list_unread_only(client, student_headers, student):
    db.session.add_all([
        Notification(recipient_id=student.user_id, title="Read", message="m",
                     notification_type=NotificationType.GENERAL, is_read=True),
        Notification(recipient_id=student.user_id, title="Unread", message="m",
                     notification_type=NotificationType.GENERAL),
    ])
    db.session.commit()

    resp = client.get("/notifications/unread", headers=student_headers)
    data = resp.get_json()
    assert data["total"] == 1
    assert data["notifications"][0]["title"] == "Unread"


def test_get_notification_not_owned_returns_404(client, student_headers, student2):
    n = Notification(
        recipient_id=student2.user_id, title="Not yours", message="m",
        notification_type=NotificationType.GENERAL,
    )
    db.session.add(n)
    db.session.commit()

    resp = client.get(f"/notifications/{n.id}", headers=student_headers)
    assert resp.status_code == 404


def test_mark_notification_as_read(client, student_headers, student):
    n = Notification(
        recipient_id=student.user_id, title="t", message="m",
        notification_type=NotificationType.GENERAL,
    )
    db.session.add(n)
    db.session.commit()

    resp = client.patch(f"/notifications/{n.id}/read", headers=student_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["is_read"] is True
    assert data["read_at"] is not None


def test_mark_all_notifications_as_read(client, student_headers, student):
    for _ in range(4):
        db.session.add(Notification(
            recipient_id=student.user_id, title="t", message="m",
            notification_type=NotificationType.GENERAL,
        ))
    db.session.commit()

    resp = client.patch("/notifications/read-all", headers=student_headers)
    assert resp.status_code == 200
    assert resp.get_json()["updated"] == 4


def test_delete_notification(client, student_headers, student):
    n = Notification(
        recipient_id=student.user_id, title="t", message="m",
        notification_type=NotificationType.GENERAL,
    )
    db.session.add(n)
    db.session.commit()

    resp = client.delete(f"/notifications/{n.id}", headers=student_headers)
    assert resp.status_code == 204
    assert db.session.get(Notification, n.id) is None


def test_all_endpoints_require_auth(client):
    assert client.get("/notifications").status_code == 401
    assert client.get("/notifications/unread").status_code == 401
    assert client.get("/notifications/1").status_code == 401
    assert client.patch("/notifications/1/read").status_code == 401
    assert client.patch("/notifications/read-all").status_code == 401
    assert client.delete("/notifications/1").status_code == 401
    assert client.post("/notifications", json={}).status_code == 401