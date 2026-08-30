# App/models/grading_system.py

from datetime import datetime, timezone
from school_app.extensions import db
from school_app.enums.grading import GradingStrategy


def _utcnow():
    return datetime.now(timezone.utc)


class GradingSystem(db.Model):
    """A named set of grading rules a school can define."""

    __tablename__ = "grading_systems"
    __table_args__ = (
        db.UniqueConstraint("school_id", "name", name="uq_grading_system_name_per_school"),
        {"extend_existing": True}
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(100), nullable=False)
    strategy = db.Column(db.Enum(GradingStrategy), nullable=False, default=GradingStrategy.LETTER_GRADE)
    is_default = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    # Relationships
    school = db.relationship("School", backref=db.backref("grading_systems", lazy="dynamic"))
    rules = db.relationship(
        "GradingRule",
        back_populates="grading_system",
        cascade="all, delete-orphan",
        order_by="GradingRule.min_score.desc()",
    )