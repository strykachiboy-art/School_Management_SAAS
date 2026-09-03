from datetime import datetime, timezone
from school_app.extensions import db
from school_app.enums.subscription import SubscriptionPlan, SubscriptionStatus, SubscriptionGateway


def _utcnow():
    return datetime.now(timezone.utc)


class Subscription(db.Model):
    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer, db.ForeignKey("schools.id", ondelete="CASCADE"),
        unique=True, nullable=False, index=True,
    )

    plan = db.Column(db.Enum(SubscriptionPlan), default=SubscriptionPlan.FREE, nullable=False)
    status = db.Column(db.Enum(SubscriptionStatus), default=SubscriptionStatus.TRIALING, nullable=False)

    gateway = db.Column(db.Enum(SubscriptionGateway), nullable=True)
    gateway_customer_id = db.Column(db.String(120), nullable=True)
    gateway_subscription_id = db.Column(db.String(120), nullable=True, index=True)

    current_period_start = db.Column(db.DateTime, nullable=True)
    current_period_end = db.Column(db.DateTime, nullable=True)
    cancel_at_period_end = db.Column(db.Boolean, default=False, nullable=False)
    canceled_at = db.Column(db.DateTime, nullable=True)

    trial_ends_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=_utcnow)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow)

    school = db.relationship("School", back_populates="subscription")

    def __repr__(self):
        return f"<Subscription school_id={self.school_id} plan={self.plan.value} status={self.status.value}>"