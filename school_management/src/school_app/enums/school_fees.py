# enums/school_fees.py

from enum import Enum


class FeeCategory(str, Enum):
    TUITION = "tuition"
    DEVELOPMENT_LEVY = "development_levy"
    PTA = "pta"
    EXAM_FEE = "exam_fee"
    UNIFORM = "uniform"
    TEXTBOOKS = "textbooks"
    TRANSPORT = "transport"
    BOARDING = "boarding"
    OTHER = "other"


class PaymentMethod(str, Enum):
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    CARD = "card"
    ONLINE = "online"
    CHEQUE = "cheque"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentGateway(str, Enum):
    PAYSTACK = "paystack"
    STRIPE = "stripe"


class InvoiceStatus(str, Enum):
    UNPAID = "unpaid"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    WAIVED = "waived"


class DiscountType(str, Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"