# App/models/promotion_rule.py

from datetime import datetime, timezone
from school_app.extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


class PromotionRule(db.Model):
    """The promotion criteria for students currently at a given AcademicLevel.

    `to_level_id` is nullable — a NULL to_level_id means this level is
    terminal (passing here means graduating, not moving to another level).
    """

    __tablename__ = "promotion_rules"
    __table_args__ = (
        db.UniqueConstraint(
            "school_id", "from_level_id", "name",
            name="uq_promotion_rule_name_per_level_per_school",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(100), nullable=False)
    from_level_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_levels.id", ondelete="CASCADE"),
        nullable=False,
    )
    to_level_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_levels.id", ondelete="SET NULL"),
        nullable=True,
    )
    min_average_score = db.Column(db.Float, nullable=True)
    min_attendance_percentage = db.Column(db.Float, nullable=True)
    min_subject_score = db.Column(db.Float, nullable=True)
    max_failed_subjects = db.Column(db.Integer, nullable=True)
    requires_admin_approval = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    # Relationships
    school = db.relationship("School", backref=db.backref("promotion_rules", lazy="dynamic"))
    from_level = db.relationship("AcademicLevel", foreign_keys=[from_level_id])
    to_level = db.relationship("AcademicLevel", foreign_keys=[to_level_id])