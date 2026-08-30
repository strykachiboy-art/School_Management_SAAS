# App/models/classroom.py

from datetime import datetime, timezone
from school_app.extensions import db
from school_app.models.association import classroom_subjects


def _utcnow():
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


class Classroom(db.Model):
    __tablename__ = "classrooms"
    __table_args__ = (
        db.UniqueConstraint("school_id", "name", name="uq_classroom_name_per_school"),
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(100), nullable=False)  # Uniqueness is scoped per school
    capacity = db.Column(db.Integer, nullable=False)
    location = db.Column(db.String(100), nullable=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)
    is_final_level = db.Column(db.Boolean, nullable=False, default=False)
    level = db.Column(db.Integer, nullable=True)
    section_id = db.Column(db.Integer, db.ForeignKey("sections.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    school = db.relationship("School", backref=db.backref("classrooms", lazy="dynamic"))
    subjects = db.relationship("Subject", back_populates="classrooms", secondary=classroom_subjects)
    teacher = db.relationship("Teacher", back_populates="classrooms", uselist=False)
    students = db.relationship("Student", back_populates="classroom")
    exams = db.relationship("Exam", back_populates="classroom")
    section = db.relationship("Section", back_populates="classrooms")
    subject_teacher_assignments = db.relationship("ClassroomSubjectTeacher", back_populates="classroom")