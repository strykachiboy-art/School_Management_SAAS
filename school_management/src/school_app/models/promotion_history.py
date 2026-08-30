# App/models/promotion_history.py

from datetime import datetime, timezone
from school_app.extensions import db
from school_app.enums.promotion import PromotionDecision


def _utcnow():
    return datetime.now(timezone.utc)


class PromotionHistory(db.Model):
    __tablename__ = "promotion_history"
    __table_args__ = (
        db.UniqueConstraint(
            "school_id", "student_id", "academic_session_id",
            name="uq_student_promotion_history_per_session_per_school",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
    )
    academic_session_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_classroom_id = db.Column(
        db.Integer,
        db.ForeignKey("classrooms.id", ondelete="SET NULL"),
        nullable=True,
    )
    to_classroom_id = db.Column(
        db.Integer,
        db.ForeignKey("classrooms.id", ondelete="SET NULL"),
        nullable=True,
    )
    decision = db.Column(db.Enum(PromotionDecision), nullable=False)
    average_score = db.Column(db.Float, nullable=True)
    attendance_percentage = db.Column(db.Float, nullable=True)
    remarks = db.Column(db.String(255), nullable=True)
    decided_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)

    # Relationships
    school = db.relationship("School", backref=db.backref("promotion_histories", lazy="dynamic"))
    student = db.relationship("Student", back_populates="promotion_history")
    academic_session = db.relationship("AcademicSession")
    from_classroom = db.relationship("Classroom", foreign_keys=[from_classroom_id])
    to_classroom = db.relationship("Classroom", foreign_keys=[to_classroom_id])
    decided_by_user = db.relationship("User", foreign_keys=[decided_by])