# App/models/onboarding_progress.py

from datetime import datetime, timezone
from school_app.extensions import db
from school_app.enums.onboarding import OnboardingStep


def _utcnow():
    return datetime.now(timezone.utc)


class OnboardingProgress(db.Model):
    """Tracks a school's progress through the setup wizard.
    """

    __tablename__ = "onboarding_progress"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # one progress record per school
        index=True,
    )

    current_step = db.Column(
        db.Enum(OnboardingStep), nullable=False, default=OnboardingStep.SCHOOL_INFO
    )
    completed_steps = db.Column(db.JSON, nullable=False, default=list)

    is_completed = db.Column(db.Boolean, nullable=False, default=False)

    started_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )

    school = db.relationship("School", backref=db.backref("onboarding_progress", uselist=False))

    def __repr__(self):
        return f"<OnboardingProgress school_id={self.school_id} current_step='{self.current_step}'>"