# App/models/result.py

from datetime import datetime, timezone
from school_app.extensions import db


def _utcnow():
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


class Result(db.Model):
    __tablename__ = "results"

    __table_args__ = (
        db.UniqueConstraint(
            "school_id",
            "student_id",
            "exam_id",
            name="uq_student_exam_result_per_school",
        ), {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    marks_obtained = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    school = db.relationship("School", backref=db.backref("results", lazy="dynamic"))
    student = db.relationship("Student", back_populates="results")
    exam = db.relationship("Exam", back_populates="results")