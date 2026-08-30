# App/models/grading_rule.py

from datetime import datetime, timezone
from school_app.extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


class GradingRule(db.Model):
    """One grade boundary within a GradingSystem — e.g. "A, min_score=70,
    remark=Excellent".
    """

    __tablename__ = "grading_rules"
    __table_args__ = (
        db.UniqueConstraint(
            "school_id", "grading_system_id", "grade_name",
            name="uq_grade_name_per_system_per_school",
        ), {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    grading_system_id = db.Column(
        db.Integer,
        db.ForeignKey("grading_systems.id", ondelete="CASCADE"),
        nullable=False,
    )
    grade_name = db.Column(db.String(20), nullable=False)
    min_score = db.Column(db.Float, nullable=False)
    max_score = db.Column(db.Float, nullable=True)
    grade_point = db.Column(db.Float, nullable=True)
    remark = db.Column(db.String(100), nullable=True)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    # Relationships
    school = db.relationship("School", backref=db.backref("grading_rules", lazy="dynamic"))
    grading_system = db.relationship("GradingSystem", back_populates="rules")