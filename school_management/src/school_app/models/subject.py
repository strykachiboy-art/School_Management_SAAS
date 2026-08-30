# App/models/subject.py

from datetime import datetime, timezone
from school_app.extensions import db
from school_app.models.association import student_subjects, classroom_subjects, teacher_subjects


def _utcnow():
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


class Subject(db.Model):
    __tablename__ = "subjects"
    __table_args__ = (
        db.UniqueConstraint("school_id", "name", name="uq_subject_name_per_school"),
        db.UniqueConstraint("school_id", "code", name="uq_subject_code_per_school"),
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )

    # Relationships
    school = db.relationship("School", backref=db.backref("subjects", lazy="dynamic"))
    students = db.relationship("Student", secondary=student_subjects, back_populates="subjects")
    teachers = db.relationship("Teacher", secondary=teacher_subjects, back_populates="subjects")
    classrooms = db.relationship("Classroom", secondary=classroom_subjects, back_populates="subjects")
    exams = db.relationship("Exam", back_populates="subject")
    classroom_teacher_assignments = db.relationship(
        "ClassroomSubjectTeacher", back_populates="subject"
    )