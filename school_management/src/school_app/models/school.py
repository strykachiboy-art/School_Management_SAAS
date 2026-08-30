# App/models/school.py

from datetime import datetime, timezone
from school_app.extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


class School(db.Model):
    """The tenant root. Every school-owned entity in this platform carries
    a direct school_id FK pointing to this table to enforce strict tenant isolation.
    """

    __tablename__ = "schools"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(100), nullable=False, unique=True, index=True)
    country = db.Column(db.String(100), nullable=True)
    timezone = db.Column(db.String(50), nullable=False, default="UTC")
    currency = db.Column(db.String(10), nullable=False, default="USD")
    locale = db.Column(db.String(10), nullable=False, default="en")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    onboarding_completed = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )

    def __repr__(self):
        return f"<School id={self.id} name='{self.name}' slug='{self.slug}'>"