import pytest
from datetime import datetime, timezone

from school_app.extensions import db
from school_app.models.notification import Notification
from school_app.enums.notification import NotificationType
from school_app.modules.notifications.services.notification_service import (
    create_notification,
    get_notification,
    get_my_notifications,
    get_unread_notifications,
    mark_notification_as_read,
    mark_all_notifications_as_read,
    delete_notification,
    notify_user,
    notify_users,
    InvalidRecipientError,
)


def test_create_notification_persists(student):
    n = create_notification(
        recipient_id=student.user_id,
        title="Exam Scheduled",
        message="Monday 9am",
        notification_type=NotificationType.EXAM,
    )
    assert n.id is not None
    assert n.is_read is False
    assert n.read_at is None
    assert db.session.get(Notification,n.id) is not None


def test_create_notification_persists_school_and_related_entity(student, school):
    n = create_notification(
        recipient_id=student.user_id,
        title="Result Published",
        message="Your result is ready",
        notification_type=NotificationType.RESULT,
        school_id=school.id,
        related_entity_type="ReportCard",
        related_entity_id=42,
    )

    assert n.school_id == school.id
    assert n.related_entity_type == "ReportCard"
    assert n.related_entity_id == 42


def test_create_notification_invalid_recipient_raises():
    with pytest.raises(InvalidRecipientError):
        create_notification(
            recipient_id=999999,
            title="t",
            message="m",
            notification_type=NotificationType.GENERAL,
        )


def test_mark_notification_as_read_is_idempotent(student):
    n = create_notification(
        recipient_id=student.user_id,
        title="t",
        message="m",
        notification_type=NotificationType.GENERAL,
    )
    first = mark_notification_as_read(n.id, student.user_id)
    first_read_at = first.read_at
    assert first_read_at is not None

    second = mark_notification_as_read(n.id, student.user_id)
    assert second.read_at == first_read_at  # unchanged on second call


def test_mark_notification_as_read_wrong_recipient_returns_none(student, student2):
    n = create_notification(
        recipient_id=student2.user_id,
        title="t",
        message="m",
        notification_type=NotificationType.GENERAL,
    )
    result = mark_notification_as_read(n.id, student.user_id)
    assert result is None


def test_mark_all_notifications_as_read_only_touches_unread(student):
    already_read = Notification(
        recipient_id=student.user_id, title="a", message="m",
        notification_type=NotificationType.GENERAL,
        is_read=True, read_at=datetime.now(timezone.utc),
    )
    db.session.add(already_read)
    for _ in range(3):
        create_notification(
            recipient_id=student.user_id,
            title="t",
            message="m",
            notification_type=NotificationType.GENERAL,
        )
    db.session.commit()

    count = mark_all_notifications_as_read(student.user_id)
    assert count == 3

    remaining_unread = Notification.query.filter_by(
        recipient_id=student.user_id, is_read=False
    ).count()
    assert remaining_unread == 0


def test_delete_notification_wrong_recipient_returns_false(student, student2):
    n = create_notification(
        recipient_id=student2.user_id,
        title="t",
        message="m",
        notification_type=NotificationType.GENERAL,
    )
    deleted = delete_notification(n.id, student.user_id)
    assert deleted is False
    assert db.session.get(Notification, n.id) is not None


def test_notify_user_creates_row(student):
    n = notify_user(
        recipient_id=student.user_id,
        title="Fees due",
        message="Term fees due Friday",
        notification_type=NotificationType.SCHOOL_FEES,
    )
    assert n.id is not None
    assert n.notification_type == NotificationType.SCHOOL_FEES


def test_notify_users_bulk_creates_rows(student, student2):
    recipients = [student.user_id, student2.user_id]
    result = notify_users(
        recipient_ids=recipients,
        title="Timetable updated",
        message="Check the new schedule",
        notification_type=NotificationType.TIMETABLE,
    )
    assert len(result) == 2

    count = Notification.query.filter(
        Notification.recipient_id.in_(recipients),
        Notification.title == "Timetable updated",
    ).count()
    assert count == 2


def test_notify_users_empty_list_noop():
    result = notify_users(
        recipient_ids=[],
        title="t",
        message="m",
        notification_type=NotificationType.GENERAL,
    )
    assert result == []