# App/models/academic_level.py

from datetime import datetime, timezone
from school_app.extensions import db


def _utcnow():
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


class AcademicLevel(db.Model):
    """A grade/year within a stage (e.g. JSS 1, Grade 7, Year 8).

    Never branch application logic on `name` — levels are school-defined and must
    be treated as opaque configuration, ordered by `display_order`.
    """

    __tablename__ = "academic_levels"
    __table_args__ = (
        db.UniqueConstraint("school_id", "stage_id", "name", name="uq_level_name_per_stage_per_school"),
        {"extend_existing": True}
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_stages.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = db.Column(db.String(100), nullable=False)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    # Relationships
    school = db.relationship("School", backref=db.backref("academic_levels", lazy="dynamic"))
    stage = db.relationship("AcademicStage", back_populates="levels")
    sections = db.relationship(
        "Section",
        back_populates="level",
        cascade="all, delete-orphan",
        order_by="Section.display_order",
    )