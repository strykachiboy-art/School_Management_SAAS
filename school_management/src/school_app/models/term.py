# App/models/term.py

from datetime import datetime, timezone
from school_app.extensions import db


def _utcnow():
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


class Term(db.Model):
    __tablename__ = "terms"
    __table_args__ = (
        db.UniqueConstraint(
            "school_id", "academic_session_id", "name",
            name="uq_term_name_per_session_per_school",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(30), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_current = db.Column(db.Boolean, default=False, nullable=False)
    academic_session_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    # Relationships
    school = db.relationship("School", backref=db.backref("terms", lazy="dynamic"))
    academic_session = db.relationship("AcademicSession", back_populates="terms")
    attendance_records = db.relationship("Attendance", back_populates="term")