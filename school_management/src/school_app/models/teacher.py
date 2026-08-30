# App/models/teacher.py

from datetime import datetime, timezone
from school_app.extensions import db
from school_app.models.association import teacher_subjects


def _utcnow():
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


class Teacher(db.Model):
    __tablename__ = "teachers"

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    # Relationships
    school = db.relationship("School", backref=db.backref("teachers", lazy="dynamic"))
    user = db.relationship("User", back_populates="teacher_profile")
    classrooms = db.relationship("Classroom", back_populates="teacher")
    subjects = db.relationship("Subject", back_populates="teachers", secondary=teacher_subjects)

    permissions = db.relationship("TeacherPermission", back_populates="teacher", cascade="all, delete-orphan")
    classroom_subject_assignments = db.relationship("ClassroomSubjectTeacher", back_populates="teacher")