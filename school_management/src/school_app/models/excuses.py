# App/models/excuse.py

from datetime import datetime, timezone
from school_app.extensions import db
from school_app.enums.excuse import ExcuseStatus


def _utcnow():
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


class Excuse(db.Model):
    __tablename__ = "excuses"

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attendance_id = db.Column(
        db.Integer,
        db.ForeignKey("attendances.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    reason = db.Column(db.String(500), nullable=False)
    status = db.Column(
        db.Enum(ExcuseStatus),
        nullable=False,
        default=ExcuseStatus.PENDING,
    )
    reviewed_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    # Relationships
    school = db.relationship("School", backref=db.backref("excuses", lazy="dynamic"))
    attendance = db.relationship("Attendance", back_populates="excuse")
    reviewer = db.relationship("User", foreign_keys=[reviewed_by])