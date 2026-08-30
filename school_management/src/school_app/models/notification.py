# App/models/notification.py

from datetime import datetime, timezone
from school_app.extensions import db
from school_app.enums.notification import NotificationType


def _utcnow():
    return datetime.now(timezone.utc)


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)

    # Tenant context (nullable to support platform/system-wide notifications)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    recipient_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title = db.Column(db.String(60), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.Enum(NotificationType), nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    read_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (
        db.Index("idx_notification_recipient_read", "recipient_id", "is_read"),
        db.Index("idx_notification_school_recipient", "school_id", "recipient_id"),
    )

    # Unidirectional relationships
    school = db.relationship("School", foreign_keys=[school_id])
    recipient = db.relationship("User", foreign_keys=[recipient_id])