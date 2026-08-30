# App/models/academic_stage.py

from datetime import datetime, timezone
from school_app.extensions import db


def _utcnow():
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


class AcademicStage(db.Model):
    """A broad academic phase (e.g. Primary, Junior Secondary, Middle School)."""

    __tablename__ = "academic_stages"
    __table_args__ = (
        db.UniqueConstraint("school_id", "name", name="uq_academic_stage_name_per_school"),
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name = db.Column(db.String(100), nullable=False)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    # Relationships
    school = db.relationship("School", backref=db.backref("academic_stages", lazy="dynamic"))
    levels = db.relationship(
        "AcademicLevel",
        back_populates="stage",
        cascade="all, delete-orphan",
        order_by="AcademicLevel.display_order",
    )