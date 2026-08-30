# App/models/exam.py

from datetime import datetime, timezone
from school_app.extensions import db
from school_app.enums.assessment import AssessmentType


def _utcnow():
    return datetime.now(timezone.utc)


class Exam(db.Model):
    __tablename__ = "exams"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey("academic_sessions.id", ondelete="CASCADE"), nullable=False)
    term_id = db.Column(db.Integer, db.ForeignKey("terms.id", ondelete="SET NULL"), nullable=True)
    start_time = db.Column(db.Time, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    total_marks = db.Column(db.Integer, nullable=False)
    assessment_type = db.Column(
        db.Enum(AssessmentType),
        nullable=False,
        default=AssessmentType.EXAMINATION,
        server_default=AssessmentType.EXAMINATION.name,
    )
    weight = db.Column(
        db.Float,
        nullable=False,
        default=100.0,
        server_default="100.0",
    )
    is_required = db.Column(db.Boolean, nullable=False, default=True, server_default="true")
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    school = db.relationship("School", backref=db.backref("exams", lazy="dynamic"))
    results = db.relationship("Result", back_populates="exam", cascade="all, delete-orphan")
    subject = db.relationship("Subject", back_populates="exams")
    classroom = db.relationship("Classroom", back_populates="exams")
    session = db.relationship("AcademicSession", back_populates="exams")
    term = db.relationship("Term", foreign_keys=[term_id])