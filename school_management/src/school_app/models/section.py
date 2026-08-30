# App/models/section.py

from datetime import datetime, timezone
from school_app.extensions import db


def _utcnow():
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


class Section(db.Model):
    """A stream within a level (e.g. A, B, Red, Science).

    Deliberately has no `capacity` field — `Classroom.capacity` since 
    the capacity is tied to the classroom.
    """

    __tablename__ = "sections"
    __table_args__ = (
        db.UniqueConstraint("school_id", "level_id", "name", name="uq_section_name_per_level_per_school"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    level_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_levels.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = db.Column(db.String(100), nullable=False)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    # Relationships
    school = db.relationship("School", backref=db.backref("sections", lazy="dynamic"))
    level = db.relationship("AcademicLevel", back_populates="sections")
    classrooms = db.relationship("Classroom", back_populates="section")