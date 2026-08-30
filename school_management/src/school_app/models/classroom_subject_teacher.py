# App/models/classroom_subject_teacher.py

from datetime import datetime, timezone
from school_app.extensions import db


def _utcnow():
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


class ClassroomSubjectTeacher(db.Model):
    """Assigns a specific teacher to teach a specific subject in a specific
    classroom, for a specific academic session.
    """

    __tablename__ = "classroom_subject_teachers"
    __table_args__ = (
        db.UniqueConstraint(
            "school_id", "classroom_id", "subject_id", "session_id",
            name="uq_one_teacher_per_classroom_subject_session_per_school",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    classroom_id = db.Column(db.Integer, db.ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey("academic_sessions.id", ondelete="CASCADE"), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    # Relationships
    school = db.relationship("School", backref=db.backref("classroom_subject_teachers", lazy="dynamic"))
    classroom = db.relationship("Classroom", back_populates="subject_teacher_assignments")
    subject = db.relationship("Subject", back_populates="classroom_teacher_assignments")
    teacher = db.relationship("Teacher", back_populates="classroom_subject_assignments")
    session = db.relationship("AcademicSession", back_populates="classroom_subject_teachers")