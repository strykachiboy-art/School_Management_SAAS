# App/models/academic_session.py

from datetime import datetime, timezone
from school_app.extensions import db


def _utcnow():
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


class AcademicSession(db.Model):
    __tablename__ = "academic_sessions"
    __table_args__ = (
        db.UniqueConstraint("school_id", "name", name="uq_academic_session_name_per_school"),
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False, default=_utcnow)
    end_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )

    # Relationships
    school = db.relationship("School", backref=db.backref("academic_sessions", lazy="dynamic"))
    terms = db.relationship("Term", back_populates="academic_session", cascade="all, delete-orphan")
    exams = db.relationship("Exam", back_populates="session")
    classroom_subject_teachers = db.relationship("ClassroomSubjectTeacher", back_populates="session")