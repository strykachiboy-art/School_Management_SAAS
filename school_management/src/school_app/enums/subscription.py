from enum import Enum


class SubscriptionPlan(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"


class SubscriptionStatus(str, Enum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    EXPIRED = "expired"


class SubscriptionGateway(str, Enum):
    PAYSTACK = "paystack"
    STRIPE = "stripe"